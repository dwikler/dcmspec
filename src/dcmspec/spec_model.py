"""DICOM specification model class for dcmspec.

Defines the SpecModel class, which represents a DICOM specification as a structured, hierarchical model.
"""
from collections import defaultdict
import logging
from typing import Optional, Dict

from anytree import Node, PreOrderIter


class SpecModel:
    """Represent a hierarchical information model from any table of DICOM documents.

    This class holds the DICOM specification model, structured into a hierarchical tree
    of DICOM components such as Data Elements, UIDs, Attributes, and others.

    The model contains two main parts:
        - metadata: a node holding table and document metadata
        - content: a node holding the hierarchical content tree

    The model can be filtered.
    """

    def __init__(
        self,
        metadata: Node,
        content: Node,
        logger: logging.Logger = None,
    ):
        """Initialize the SpecModel.

        Sets up the logger and initializes the specification model.

        Args:
            metadata (Node): Node holding table and document metadata, such as headers, version, and table ID.
            content (Node): Node holding the hierarchical content tree of the DICOM specification.
            logger (logging.Logger, optional): A pre-configured logger instance to use.
                If None, a default logger will be created.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.metadata = metadata
        self.content = content

    def exclude_titles(self) -> None:
        """Remove nodes corresponding to title rows from the content tree.

        Title rows are typically found in some DICOM tables and represent section headers
        rather than actual data elements (such as Module titles in PS3.4). 
        This method traverses the content tree and removes any node identified as a title,
        cleaning up the model for further processing.

        The method operates on the content tree and does not affect the metadata node.

        Returns:
            None

        """
        # Traverse the tree and remove nodes where is_title is True
        for node in list(PreOrderIter(self.content)):
            if self._is_title(node):
                self.logger.debug(f"Removing title node: {node.name}")
                node.parent = None

    def filter_required(self, type_attr_name: str, keep: Optional[str] = None, remove: Optional[str] = None) -> None:
        """Remove nodes that are considered optional according to DICOM requirements.

        This method traverses the content tree and removes nodes whose requirement
        (e.g., "Type", "Matching", or "Return Key") indicates that they are optional. 
        Nodes with conditional or required types (e.g., "1", "1C", "2", "2C")
        are retained. The method can be customized by specifying which types to keep or remove.

        Additionally, for nodes representing Sequences (node names containing "_sequence"), 
        this method removes all subelements if the sequence itself is not required or can be empty
        (e.g., type "3", "2", "2C", "-", "O", or "Not allowed").

        Args:
            type_attr_name (str): Name of the node attribute holding the optionality requirement,
                for example "Type" of an attribute, "Matching", or "Return Key".
            keep (Optional[list[str]]): List of type values to keep (default: ["1", "1C", "2", "2C"]).
            remove (Optional[list[str]]): List of type values to remove (default: ["3"]).

        Returns:
            None

        """
        if keep is None:
            keep = ["1", "1C", "2", "2C"]
        if remove is None:
            remove = ["3"]
        types_to_keep = keep
        types_to_remove = remove
        attribute_name = type_attr_name

        for node in PreOrderIter(self.content):
            if hasattr(node, attribute_name):
                dcmtype = getattr(node, attribute_name)
                if dcmtype in types_to_remove and dcmtype not in types_to_keep:
                    self.logger.debug(f"[{dcmtype.rjust(3)}] : Removing {node.name} element")
                    node.parent = None

            # Remove nodes under "Sequence" nodes which are not required or which can be empty
            if "_sequence" in node.name and hasattr(node, attribute_name):
                dcmtype = getattr(node, attribute_name)
                if dcmtype in ["3", "2", "2C", "-", "O", "Not allowed"]:
                    self.logger.debug(f"[{dcmtype.rjust(3)}] : Removing {node.name} subelements")
                    for descendant in node.descendants:
                        descendant.parent = None

    def merge_matching_path(
        self,
        other: "SpecModel",
        match_by: str = "name",  # or "attribute"
        attribute_name: Optional[str] = None,
        merge_attrs: Optional[list[str]] = None,
    ) -> "SpecModel":
        """Merge with another SpecModel, producing a new model with attributes merged for nodes with matching paths.

        The path for matching is constructed at each level using either the node's `name`
        (if match_by="name") or a specified attribute (if match_by="attribute" and attribute_name is given).
        Only nodes whose full path matches (by the chosen key) will be merged.

        This method is useful for combining DICOM specification models from different parts of the standard.
        For example, it can be used to merge a PS3.3 model of a normalized IOD specification with a PS3.4 model of a
        SOP class specification.

        Args:
            other (SpecModel): The other model to merge with the current model.
            match_by (str): "name" to match by node.name path, "attribute" to match by a specific attribute path.
            attribute_name (str, optional): The attribute name to use for matching if match_by="attribute".
            merge_attrs (list[str], optional): List of attribute names to merge from the other model's node.

        Returns:
            SpecModel: A new merged SpecModel.

        """
        import copy
        merged = copy.deepcopy(self)

        # Build a dict mapping node path (the matchkey) to nodes in the 'other' model
        if match_by == "name":
            other_matchkey_to_node_map = {
                self._get_path_by_name(node): node
                for node in PreOrderIter(other.content)
            }
            def get_path(node): return self._get_path_by_name(node)

        elif match_by == "attribute" and attribute_name:
            other_matchkey_to_node_map = {
                self._get_path_by_attr(node, attribute_name): node
                for node in PreOrderIter(other.content)
            }
            def get_path(node): return self._get_path_by_attr(node, attribute_name)
            
        else:
            raise ValueError("Invalid match_by or missing attribute_name")

        # Merge attributes
        for node in PreOrderIter(merged.content):
            key = get_path(node)
            if key in other_matchkey_to_node_map:
                other_node = other_matchkey_to_node_map[key]
                for attr in (merge_attrs or []):
                    if attr is not None and hasattr(other_node, attr):
                        setattr(node, attr, getattr(other_node, attr))

        return merged

    def merge_matching_node(
        self,
        other: "SpecModel",
        match_by: str = "name",  # or "attribute"
        attribute_name: Optional[str] = None,
        merge_attrs: Optional[list[str]] = None,
    ) -> "SpecModel":
        """Merge two SpecModel trees by matching nodes at any level using a single key (name or attribute).

        For each node in the current model, this method finds a matching node in the other model
        using either the node's name (if match_by="name") or a specified attribute (if match_by="attribute").
        If a match is found, the specified attributes from the other model's node are merged into the current node.

        This is useful for enrichment scenarios, such as adding VR/VM/Keyword from the Part 6 dictionary
        to a Part 3 module, where nodes are matched by a unique attribute like elem_tag.

        - Matching is performed globally (not by path): any node in the current model is matched to any node
          in the other model with the same key value, regardless of their position in the tree.
        - It is expected that there is only one matching node per key in the other model.
        - If multiple nodes in the other model have the same key, a warning is logged and only the last one
          found in pre-order traversal is used for merging.

        Example use cases:
            - Enrich a PS3.3 module attribute specification with VR/VM from the PS3.6 data elements dictionary.
            - Merge any two models where a unique key (name or attribute) can be used for node correspondence.

        Args:
            other (SpecModel): The other model to merge with the current model.
            match_by (str): "name" to match by node.name (stripped of leading '>' and whitespace),
                or "attribute" to match by a specific attribute value.
            attribute_name (str, optional): The attribute name to use for matching if match_by="attribute".
            merge_attrs (list[str], optional): List of attribute names to merge from the other model's node.

        Returns:
            SpecModel: A new merged SpecModel with attributes from the other model merged in.

        Raises:
            ValueError: If match_by is invalid or attribute_name is missing when required.

        """
        import copy
        merged = copy.deepcopy(self)

        # Build a dict mapping matching node or attribute name (the matchkey) to nodes in the 'other' model
        if match_by == "name":
            self.logger.debug("Matching models by node name (stripped of leading > and whitespace).")
            def key_func(node):
                return self._strip_leading_gt(node.name)
        elif match_by == "attribute" and attribute_name:
            self.logger.debug(f"Matching models by attribute name: {attribute_name}.")
            def key_func(node):
                return getattr(node, attribute_name, None)
        else:
            raise ValueError(
                f"Invalid match_by value '{match_by}'. "
                f"Valid options are 'name' or 'attribute'. "
                f"If using 'attribute', attribute_name must be provided."
            )

        # Build a mapping from key to list of nodes
        key_to_nodes = defaultdict(list)
        for node in PreOrderIter(other.content):
            key = key_func(node)
            key_to_nodes[key].append(node)

        # Warn if any key has more than one node
        for key, nodes in key_to_nodes.items():
            if key is not None and len(nodes) > 1:
                self.logger.warning(
                    f"Multiple nodes found in 'other' model for key '{key}': "
                    f"{[getattr(n, 'name', None) for n in nodes]}. "
                    "Only the last one will be used for merging."
                )

        # Use only the last node for each key (to preserve current behavior)
        other_matchkey_to_node_map = {key: nodes[-1] for key, nodes in key_to_nodes.items()}
        def get_key(node): return key_func(node)
        # Merge attributes for any matching node
        for node in PreOrderIter(merged.content):
            key = get_key(node)
            if key in other_matchkey_to_node_map and key is not None:
                other_node = other_matchkey_to_node_map[key]
                for attr in (merge_attrs or []):
                    if attr is not None and hasattr(other_node, attr):
                        setattr(node, attr, getattr(other_node, attr))
                        self.logger.debug(f"Enriched node {getattr(node, 'name', None)} "
                                          f"(key={key}) with {attr}={getattr(other_node, attr)}")
            else:
                self.logger.debug(f"No match for node {getattr(node, 'name', None)} (key={key})")
        return merged

    def _strip_leading_gt(self, name):
        """Strip leading '>' and whitespace from a node name for matching."""
        return name.lstrip(">").lstrip().rstrip() if isinstance(name, str) else name

    def _is_include(self, node: Node) -> bool:
        """Determine if a node represents an 'Include' of a Macro table.

        Args:
            node: The node to check.

        Returns:
            True if the node represents an 'Include' of a Macro table, False otherwise.

        """
        return "include_table" in node.name

    def _is_title(self, node: Node) -> bool:
        """Determine if a node is a title.

        Args:
            node: The node to check.

        Returns:
            True if the node is a title, False otherwise.

        """
        return (
            self._has_only_key_0_attr(node, self.metadata.column_to_attr)
            and not self._is_include(node)
            and node.name != "content"
        )

    def _has_only_key_0_attr(self, node: Node, column_to_attr: Dict[int, str]) -> bool:
        # sourcery skip: merge-duplicate-blocks, use-any
        """Check that only the key 0 attribute is present.

        Determines if a node has only the attribute specified by the item with key "0"
        in column_to_attr, corresponding to the first column of the table.

        Args:
            node: The node to check.
            column_to_attr: Mapping between column number and attribute name.

        Returns:
            True if the node has only the key "0" attribute, False otherwise.

        """
        # Irrelevant if columns 0 not extracted
        if 0 not in column_to_attr:
            return False

        # Check that only the key 0 attribute is present
        key_0_attr = column_to_attr[0]
        for key, attr_name in column_to_attr.items():
            if key == 0:
                if not hasattr(node, key_0_attr):
                    return False
            elif hasattr(node, attr_name):
                return False
        return True

    @staticmethod
    def _get_node_path(node: Node, attr: str = "name") -> tuple:
        """Return a tuple representing the path of the node using the given attribute."""
        return tuple(getattr(n, attr, None) for n in node.path)


    @staticmethod
    def _get_path_by_name(node: Node) -> tuple:
        """Return the path of the node using node.name at each level."""
        return SpecModel._get_node_path(node, "name")

    @staticmethod
    def _get_path_by_attr(node: Node, attr: str) -> tuple:
        """Return the path of the node using the given attribute at each level."""
        return SpecModel._get_node_path(node, attr)
