"""DICOM specification model class for dcmspec.

Defines the SpecModel class, which represents a DICOM specification as a structured, hierarchical model.
"""
from collections import defaultdict
import copy
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

    def filter_required(
        self,
        type_attr_name: str,
        keep: Optional[list[str]] = None,
        remove: Optional[list[str]] = None
    ) -> None:
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
                if "_sequence" in node.name and dcmtype in ["3", "2", "2C", "-", "O", "Not allowed"]:
                    self.logger.debug(f"[{dcmtype.rjust(3)}] : Removing {node.name} subelements")
                    for descendant in node.descendants:
                        descendant.parent = None

    def merge_matching_path(
        self,
        other: "SpecModel",
        match_by: str = "name",
        attribute_name: Optional[str] = None,
        merge_attrs: Optional[list[str]] = None,
        ignore_module_level: bool = False,
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
            ignore_module_level (bool, optional): If True, skip the module level in the path for matching.

        Returns:
            SpecModel: A new merged SpecModel.

        """        
        return self._merge_nodes(
            other,
            match_by=match_by,
            attribute_name=attribute_name,
            merge_attrs=merge_attrs,
            is_path_based=True,
            ignore_module_level=ignore_module_level
        )

    def merge_matching_node(
        self,
        other: "SpecModel",
        match_by: str = "name",
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
        return self._merge_nodes(
            other,
            match_by=match_by,
            attribute_name=attribute_name,
            merge_attrs=merge_attrs,
            is_path_based=False
        )
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

        key_0_attr = column_to_attr[0]
        # key 0 must be present and not None
        if not hasattr(node, key_0_attr) or getattr(node, key_0_attr) is None:
            return False

        # all other keys must be absent or None
        for key, attr_name in column_to_attr.items():
            if key == 0:
                continue
            if hasattr(node, attr_name) and getattr(node, attr_name) is not None:
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

    def _build_node_map(
        self,
        other: "SpecModel",
        match_by: str,
        attribute_name: Optional[str] = None,
        is_path_based: bool = False
    ) -> tuple[dict, callable]:
        """Construct a mapping from keys to nodes in the other model, and a key function for matching.

        This method prepares the data structures needed for merging two SpecModel trees. It builds a mapping
        from a key (either a node's name, a specified attribute, or a path of such values) to nodes in the
        `other` model, and returns a function that computes the same key for nodes in the current model.

        Args:
            other (SpecModel): The other model to merge with.
            match_by (str): "name" to match by node name, or "attribute" to match by a specific attribute.
            attribute_name (str, optional): The attribute name to use for matching if match_by="attribute".
            is_path_based (bool): If True, use the full path of names/attributes as the key; if False, 
                use only the value.

        Returns:
            tuple: (node_map, key_func)
                node_map (dict): Mapping from key to node in the other model.
                key_func (callable): Function that computes the key for a node in the current model.

        Raises:
            ValueError: If match_by is invalid or attribute_name is missing when required.

        """
        if match_by == "name":
            self.logger.debug("Matching models by node name.")
            if is_path_based:
                node_map = {
                    self._get_path_by_name(node): node
                    for node in PreOrderIter(other.content)
                }
                def key_func(node):
                    return self._get_path_by_name(node)
            else:
                def key_func(node):
                    return self._strip_leading_gt(node.name)
                # Build mapping with handling of duplicates
                key_to_nodes = defaultdict(list)
                for node in PreOrderIter(other.content):
                    key = key_func(node)
                    key_to_nodes[key].append(node)
                
                self._warn_multiple_matches(key_to_nodes)
                node_map = {key: nodes[-1] for key, nodes in key_to_nodes.items()}
                
        elif match_by == "attribute" and attribute_name:
            self.logger.debug(f"Matching models by attribute: {attribute_name}")
            if is_path_based:
                node_map = {
                    self._get_path_by_attr(node, attribute_name): node
                    for node in PreOrderIter(other.content)
                }
                def key_func(node):
                    return self._get_path_by_attr(node, attribute_name)
            else:
                def key_func(node):
                    return getattr(node, attribute_name, None)
                # Build mapping with handling of duplicates
                key_to_nodes = defaultdict(list)
                for node in PreOrderIter(other.content):
                    key = key_func(node)
                    key_to_nodes[key].append(node)
                
                self._warn_multiple_matches(key_to_nodes)
                node_map = {key: nodes[-1] for key, nodes in key_to_nodes.items()}
        else:
            raise ValueError("Invalid match_by or missing attribute_name")
            
        return node_map, key_func

    def _warn_multiple_matches(self, key_to_nodes: dict):
        """Log a warning if any key in the mapping corresponds to multiple nodes.

        Args:
            key_to_nodes (dict): A mapping from key to a list of nodes with that key.

        Returns:
            None

        """
        for key, nodes in key_to_nodes.items():
            if key is not None and len(nodes) > 1:
                self.logger.warning(
                    f"Multiple nodes found for key '{key}': "
                    f"{[getattr(n, 'name', None) for n in nodes]}. "
                    "Only the last one will be used for merging."
                )

    def _merge_nodes(
        self,
        other: "SpecModel",
        match_by: str,
        attribute_name: Optional[str] = None,
        merge_attrs: Optional[list[str]] = None,
        is_path_based: bool = False,
        ignore_module_level: bool = False,
    ) -> "SpecModel":
        """Merge this SpecModel with another, enriching nodes by matching keys.

        This is the core logic for merging two SpecModel trees. For each node in the current model,
        it attempts to find a matching node in the other model using the specified matching strategy.
        If a match is found, the specified attributes from the other node are copied into the current node.

        Args:
            other (SpecModel): The other model to merge from.
            match_by (str): "name" to match by node name, or "attribute" to match by a specific attribute.
            attribute_name (str, optional): The attribute name to use for matching if match_by="attribute".
            merge_attrs (list[str], optional): List of attribute names to copy from the matching node.
            is_path_based (bool): If True, match nodes by their full path; if False, match globally by key.
            ignore_module_level (bool): If True, skip the module level in the path for matching.

        Returns:
            SpecModel: A deep copy of this model, with attributes merged from the other model where matches are found.

        Notes:
            - If multiple nodes in the other model have the same key, only the last one is used (a warning is logged).
            - If a node in this model has no match in the other model, it is left unchanged.
            - The merge is non-destructive: a new SpecModel is returned.

        """
        merged = copy.deepcopy(self)
        merged.logger = self.logger 

        if is_path_based and ignore_module_level:
            # Build node_map with stripped paths
            if match_by == "name":
                node_map = {
                    self._strip_module_level(self._get_path_by_name(node)): node
                    for node in PreOrderIter(other.content)
                }
                def key_func(node):
                    return self._strip_module_level(self._get_path_by_name(node))
            elif match_by == "attribute" and attribute_name:
                node_map = {
                    self._strip_module_level(self._get_path_by_attr(node, attribute_name)): node
                    for node in PreOrderIter(other.content)
                }
                def key_func(node):
                    return self._strip_module_level(self._get_path_by_attr(node, attribute_name))
            else:
                raise ValueError("Invalid match_by or missing attribute_name")
        else:
            node_map, key_func = self._build_node_map(
                other, match_by, attribute_name, is_path_based
            )

        enriched_count = 0
        total_nodes = 0
        for node in PreOrderIter(merged.content):
            total_nodes += 1
            key = key_func(node)

            if key in node_map and key is not None:
                other_node = node_map[key]
                enriched_this_node = False
                for attr in (merge_attrs or []):
                    if attr is not None and hasattr(other_node, attr):
                        setattr(node, attr, getattr(other_node, attr))
                        attr_val = getattr(other_node, attr)
                        self.logger.debug(
                            f"Enriched node {getattr(node, 'name', None)} "
                            f"(key={key}) with {attr}={str(attr_val)[:10]}"
                        )
                        enriched_this_node = True
                if enriched_this_node:
                    enriched_count += 1

        self.logger.info(f"Total nodes enriched during merge: {enriched_count} / {total_nodes}")
        return merged

    def _strip_module_level(self, path_tuple):
        # Remove all but the last leading None or the module level for path matching
        # This ensures (None, None, '(0010,0010)') and (None, '(0010,0010)') both become (None, '(0010,0010)')
        path = list(path_tuple)
        while len(path) > 2 and path[0] is None:
            path.pop(0)
        return tuple(path)