"""Printer class for specification model in dcmspec.

Provides the SpecPrinter class for printing DICOM specification models (SpecModel)
to standard output, either as a hierarchical tree or as a flat table, using rich formatting.
"""
from rich.console import Console
from rich.table import Table, box
from rich.text import Text
from anytree import RenderTree, PreOrderIter
from typing import Optional, List, Union
import logging

LEVEL_COLORS = [
    "rgb(255,255,255)",  # Node depth 0, Root: White
    "rgb(173,216,230)",  # Node depth 1, Table Level 0: Light Blue
    "rgb(135,206,250)",  # Node depth 2, Table Level 1: Sky Blue
    "rgb(0,191,255)",  # Node depth 3, Table Level 2: Deep Sky Blue
    "rgb(30,144,255)",  # Node depth 4, Table Level 3: Dodger Blue
    "rgb(0,0,255)",  # Node depth 5, Table Level 4: Blue
]

class SpecPrinter:
    """Printer for DICOM specification models.

    Provides methods to print a SpecModel as a hierarchical tree or as a flat table,
    using rich formatting for console output. Supports colorized output and customizable logging.
    """

    def __init__(self, model: object, logger: Optional[logging.Logger] = None) -> None:
        """Initialize the input handler with an optional logger.

        Args:
            model (object): An instance of SpecModel.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.model = model
        self.console = Console(highlight=False)

    def print_tree(
        self,
        attr_names: Optional[Union[str, List[str]]] = None,
        attr_widths: Optional[List[int]] = None,
        colorize: bool = False,
    ) -> None:
        """Print the specification model as a hierarchical tree to the console.

        Args:
            attr_names (Optional[Union[str, list[str]]]): Attribute name(s) to display for each node.
                If None, only the node's name is displayed.
                If a string, displays that single attribute.
                If a list of strings, displays all specified attributes.
            attr_widths (Optional[list[int]]): List of widths for each attribute in attr_names.
                If provided, each attribute will be padded/truncated to the specified width.
            colorize (bool): Whether to colorize the output by node depth.

        Returns:
            None

        
        Example:
            ```python
            # This will nicely align the tag, type, and name values in the tree output:
            printer.print_tree(attr_names=["elem_tag", "elem_type", "elem_name"], attr_widths=[11, 2, 64])
            ```
            
        """
        for pre, fill, node in RenderTree(self.model.content):
            style = LEVEL_COLORS[node.depth % len(LEVEL_COLORS)] if colorize else "default"
            pre_text = Text(pre)
            if attr_names is None:
                node_text = Text(str(node.name), style=style)
            else:
                if isinstance(attr_names, str):
                    attr_names = [attr_names]
                values = [str(getattr(node, attr, "")) for attr in attr_names]
                if attr_widths:
                    # Pad/truncate each value to the specified width
                    values = [
                        v.ljust(w)[:w] if w is not None else v
                        for v, w in zip(values, attr_widths)
                    ]
                attr_text = " ".join(values)
                node_text = Text(attr_text, style=style)
            self.console.print(pre_text + node_text)

    def print_table(self, colorize: bool = False) -> None:
        """Print the specification model as a flat table to the console.

        Traverses the content tree and prints each node's attributes in a flat table,
        using column headers from the metadata node. Optionally colorizes rows.

        Args:
            colorize (bool): Whether to colorize the output by node depth.

        Returns:
            None
            
        """
        table = Table(show_header=True, header_style="bold magenta", show_lines=True, box=box.ASCII_DOUBLE_HEAD)

        # Define the columns using the extracted headers
        for header in self.model.metadata.header:
            table.add_column(header, width=20)

        # Traverse the tree and add rows to the table
        for node in PreOrderIter(self.model.content):
            # skip the root node
            if node.name == "content":
                continue
            
            row = [getattr(node, attr, "") for attr in self.model.metadata.column_to_attr.values()]
            # Skip row if all values are empty or whitespace
            if all(not str(cell).strip() for cell in row):
                continue
            row_style = None
            if colorize:
                row_style = (
                    "yellow"
                    if self.model._is_include(node)
                    else "magenta"
                    if self.model._is_title(node)
                    else LEVEL_COLORS[(node.depth - 1) % len(LEVEL_COLORS)]
                )
            table.add_row(*row, style=row_style)

        self.console.print(table)
