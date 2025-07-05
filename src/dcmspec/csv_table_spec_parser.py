"""CSV specification parser class for IHE profiles tables in dcmspec.

Provides the CSVTableSpecParser class for parsing DICOM specification tables in CSV format,
converting them into structured in-memory representations using anytree.
"""
from typing import Tuple
from anytree import Node

from dcmspec.spec_parser import SpecParser

class CSVTableSpecParser(SpecParser):
    """Base parser for DICOM Specification IHE tables in CSV-like format."""

    def parse(
        self,
        table: dict,
        column_to_attr,
        name_attr="elem_name",
        table_id=None,
        include_depth=None,
    ) -> Tuple[Node, Node]:
        """Parse specification metadata and content from a single table dict.

        Args:
            table (dict): A table dict as output by PDFDocHandler.concat_tables, with 'header' and 'data' keys.
            column_to_attr (dict): Mapping from column indices to node attribute names.
            name_attr (str): The attribute to use for node names.
            table_id (str, optional): Table identifier for model parsing.
            include_depth (int, optional): The depth to which included tables should be parsed.

        Returns:
            tuple: (metadata_node, content_node)

        """
        # Use the header and data from the grouped table dict
        header = table.get("header", [])
        data = table.get("data", [])

        metadata = Node("metadata")
        metadata.header = header
        metadata.column_to_attr = column_to_attr
        metadata.table_id = table_id
        if include_depth is not None:
            metadata.include_depth = int(include_depth)
        content = self.parse_table([data], column_to_attr, name_attr)
        return metadata, content

    def parse_table(
        self,
        tables: list,  # List of tables, each a list of rows (list of str)
        column_to_attr: dict,
        name_attr: str = "elem_name",
    ) -> Node:
        """Build a tree from tables using column mapping and '>' nesting logic.

        Args:
            tables (list): List of tables, each a list of rows (list of str).
            column_to_attr (dict): Mapping from column indices to node attribute names.
            name_attr (str): The attribute to use for node names.

        Returns:
            Node: The root node of the tree.

        """
        root = Node("content")
        parent_nodes = {0: root}
        for table in tables:
            for row in table:
                row_data = {}
                for col_idx, attr in column_to_attr.items():
                    value = row[col_idx] if col_idx < len(row) else ""
                    # Clean up newlines in the cell to be used as node name
                    if attr == name_attr:
                        value = value.replace("\n", " ")
                    row_data[attr] = value
                node_name = row_data[name_attr]
                level = node_name.count(">") + 1
                # Ensure all parent levels exist
                if (level - 1) not in parent_nodes:
                    # If a parent is missing, attach to root
                    parent_nodes[level - 1] = root
                parent = parent_nodes[level - 1]
                child = Node(node_name, parent=parent, **row_data)
                parent_nodes[level] = child
        return root
