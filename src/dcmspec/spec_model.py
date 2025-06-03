"""DICOM specification model class for dcmspec.

Defines the SpecModel class, which represents a DICOM specification as a structured, hierarchical model.
"""
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
        """Initialize the DICOMAttributeModel.

        Sets up the logger and initializes the attribute model.

        Args:
            metadata (Node): Node holding table and document metadata, such as headers, version, and table ID.
            content (Node): Node holding the hierarchical content tree of the DICOM specification.
            logger (logging.Logger, optional): A pre-configured logger instance to use.
                If None, a default logger will be created.

        """
        self.logger = logger or self._create_default_logger()

        self.metadata = metadata
        self.content = content

    def exclude_titles(self):
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

    def filter_required(self, type_attr_name: str, keep: Optional[str] = None, remove: Optional[str] = None):
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

    def _create_default_logger(self):
        """Create a default logger for the class.

        Configures a logger with a console handler and a specific format.
        """
        logger = logging.getLogger("DICOMAttributeModel")
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger

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
        """Check for presence of only the key 0 attribute.

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
        
        # Perform the check
        key_0_attr = column_to_attr[0]
        for key, attr_name in column_to_attr.items():
            if key == 0:
                if not hasattr(node, key_0_attr):
                    return False
            else:
                if hasattr(node, attr_name):
                    return False
        return True
