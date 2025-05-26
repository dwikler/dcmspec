import logging
from typing import Optional, Dict

from anytree import Node, PreOrderIter


class SpecModel:
    """
    Builds a hierarchical information model from any DICOM table in HTML format.

    This class holds the DICOM specification model, structured into a hierarchical tree
    of DICOM components such as Data Elements, UIDs, Attributes and others.

    The model can be filtered.
    """

    def __init__(
        self,
        metadata: Node,
        content: Node,
        logger: logging.Logger = None,
    ):
        """
        Initializes the DICOMAttributeModel.

        Sets up the logger and initializes the attribute model.

        Args:
            metadata
            content
            table_id (str, optional): The ID of the table to process. Defaults to None.
            include_depth (int, optional): The depth of include expansion. Defaults to 0.
            logger (logging.Logger, optional): A pre-configured logger instance to use.
                    If None, a default logger will be created.

        """
        self.logger = logger or self._create_default_logger()

        self.metadata = metadata
        self.content = content

    def exclude_module_titles(self):
        """Removes nodes corresponding to Module title rows as found in some PS3.4 tables"""

        # Traverse the tree and remove nodes where is_module_title is True
        for node in list(PreOrderIter(self.content)):
            if self._is_module_title(node):
                self.logger.debug(f"Removing Module title node: {node.name}")
                node.parent = None

    def filter_required(
        self,
        type_attr_name: str,
        keep: Optional[str] = ["1", "1C", "2", "2C"],
        remove: Optional[str] = ["3"],
    ):
        """
        Removes nodes that are optional. Optional means that they do not need to be present
        for sure (nodes with conditional or other requirement are retained).

        Args:
            type_attr_name: Name of the node attribute hodling the optionality requirement,
            for example Type of an attribute or Matching or Return Key.
        """
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
        """
        Creates a default logger for the class.

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
        """
        Determines if a node represents an 'Include' table.

        Args:
            node: The node to check.

        Returns:
            True if the node represents an 'Include' table, False otherwise.
        """
        return "include_table" in node.name

    def _is_module_title(self, node: Node) -> bool:
        """
        Determines if a node is a Module title.

        Args:
            node: The node to check.

        Returns:
            True if the node is a module title, False otherwise.
        """
        return (
            self._has_only_key_0_attr(node, self.metadata.column_to_attr)
            and not self._is_include(node)
            and node.name != "content"
        )

    def _has_only_key_0_attr(self, node: Node, column_to_attr: Dict[int, str]) -> bool:
        """
        Check if a node has only the attribute specified by the item with key "0",
        corresponding to the first column of the table.

        Args:
            node: The node to check.
            column_to_attr: Mapping between column number and attribute name

        Returns:
            True if the node has only the key "0" attribute.
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
