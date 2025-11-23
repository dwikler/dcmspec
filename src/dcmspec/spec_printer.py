"""Printer class for specification model in dcmspec.

Provides the SpecPrinter class for printing DICOM specification models (SpecModel)
to a file or standard output.
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

    Provides methods to render a SpecModel in multiple formats:
    - Hierarchical tree (ASCII)
    - Flat table (ASCII, using Rich for styling)
    - CSV (plain text)

    Output can be directed to the console (default) or to a file by specifying
    an output path when initializing the printer. Rich formatting is used for
    tree and table views when writing to the console; when writing to a file,
    plain text is used.

    Responsibilities:
    - Encapsulates all presentation logic for SpecModel.
    - Supports colorized output for better readability.
    - Handles output destination internally (stdout or file).

    Args:
        model (SpecModel): The specification model to print.
        output (Optional[str]): Path to an output file. If None, prints to stdout.
        logger (Optional[logging.Logger]): Logger instance for debug/info messages.
    """

    def __init__(self, model: object, output: Optional[str] = None, logger: Optional[logging.Logger] = None) -> None:
        """Initialize the printer with a specification model and optional output destination.

        Args:
            model (object): An instance of SpecModel to render.
            output (Optional[str]): Path to an output file. If None, defaults to stdout.
            logger (Optional[logging.Logger]): Logger instance for debug/info messages.
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.model = model
        self.output = output
        # Disable styling when writing to file
        self.console = Console(
            highlight=False,
            file=open(output, "w", encoding="utf-8") if output else None,
            force_terminal=not output,
            no_color=bool(output)
        )

    def print_tree(
        self,
        attr_names: Optional[Union[str, List[str]]] = None,
        attr_widths: Optional[List[int]] = None,
        colorize: bool = False,
    ) -> None:
        """Print the specification model as a hierarchical tree to the console or file.

        Args:
            attr_names (Optional[Union[str, list[str]]]): Attribute name(s) to display for each node.
                If None, only the node's name is displayed.
                If a string, displays that single attribute.
                If a list of strings, displays all specified attributes.
            attr_widths (Optional[list[int]]): List of widths for each attribute in attr_names.
                If provided, each attribute will be padded/truncated to the specified width.
            colorize (bool): Whether to colorize the output by node depth. Ignored when writing to file.

        Returns:
            None

        
        Example:
            ```python
            # This will nicely align the tag, type, and name values in the tree output:
            printer.print_tree(attr_names=["elem_tag", "elem_type", "elem_name"], attr_widths=[11, 2, 64])
            ```
            
        """
        # Disable colorization if writing to file
        if self.output:
            colorize = False
            
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
        """Print the specification model as an ascii table to the console or file.

        Traverses the content tree and prints each node's attributes in a flat table,
        using column headers from the metadata node. Optionally colorizes rows.

        Args:
            colorize (bool): Whether to colorize the output by node depth. Ignored when writing to file.

        Returns:
            None
            
        """
        # Disable colorization if writing to file
        if self.output:
            colorize = False
            
        table = Table(show_header=True, header_style="bold magenta", show_lines=True, box=box.ASCII_DOUBLE_HEAD)

        # Define the columns using the extracted headers
        for header in self.model.metadata.header:
            table.add_column(header, width=20)

        # Add rows to the table
        for row, row_style in self._iterate_rows(colorize):
            table.add_row(*row, style=row_style)

        self.console.print(table)

    def print_csv(self, colorize: bool = False) -> None:
        """Print the specification model as CSV to the console or file.

        Traverses the content tree and prints each node's attributes in CSV format,
        with column headers from the metadata node. Optionally colorizes rows.

        Args:
            colorize (bool): Whether to colorize the output by node depth. Ignored when writing to file.

        Returns:
            None
            
        """
        # Disable colorization if writing to file
        if self.output:
            colorize = False
            
        # Print CSV header
        header_row = ",".join(f'"{h}"' for h in self.model.metadata.header)
        self.console.print(header_row)

        # Add data rows
        for row, row_style in self._iterate_rows(colorize):
            # Escape quotes inside each field by doubling them 
            # (e.g., Include Table 10.29-1 "UDI Macro Attributes"→ Include Table 10.29-1 ""UDI Macro Attributes""),
            # then wrap the entire field in quotes for proper CSV formatting
            csv_row = ",".join(f'"{cell.replace(chr(34), chr(34) + chr(34))}"' for cell in row)
            self.console.print(csv_row, style=row_style)

    def _iterate_rows(self, colorize: bool = False):
        """Generate rows from the model tree with optional styling.

        Args:
            colorize (bool): Whether to apply color styling to rows.

        Yields:
            tuple: (row_data, row_style) where row_data is a list of cell values
                   and row_style is the color style string or None.
        """
        for node in PreOrderIter(self.model.content):
            # skip the root node
            if node.name == "content":
                continue
            
            row = [str(getattr(node, attr, "")) for attr in self.model.metadata.column_to_attr.values()]
            # Skip row if all values are empty or whitespace
            if all(not cell.strip() for cell in row):
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
            
            yield row, row_style

    def __del__(self):
        """Close output file when the printer is deleted, if opened."""
        if self.output and hasattr(self.console, 'file') and self.console.file:
            self.console.file.close()
