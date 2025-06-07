"""Printer class for DICOM IOD specification model in dcmspec.

Provides the SpecPrinter class for printing DICOM IOD specification models (SpecModel)
to standard output, either as a hierarchical tree or as a flat table, using rich formatting.
"""
from anytree import PreOrderIter
from rich.table import Table, box

from dcmspec.spec_printer import LEVEL_COLORS, SpecPrinter

class IODSpecPrinter(SpecPrinter):
    """Printer for DICOM IOD specification models with mixed node types.

    Overrides print_table to display IOD Modules nodes as a one-cell title row (spanning all columns)
    The table columns are those of the Module Attributes nodes.
    """

    def print_table(self, colorize: bool = False):
        """Print the specification model as a flat table with module title rows.

        Args:
            colorize (bool): Whether to colorize the output by node depth.

        """
        table = Table(show_header=True, header_style="bold magenta", show_lines=True, box=box.ASCII_DOUBLE_HEAD)

        attr_headers = list(self.model.metadata.header)
        for header in attr_headers:
            table.add_column(header, width=20)

        # Traverse the tree in PreOrder (as in the base class)
        for node in PreOrderIter(self.model.content):
            # skip the root node
            if node.name == "content":
                continue            # Print IOD module nodes as a title row (one cell, spanning all columns)
            if hasattr(node, "module"):
                iod_title = getattr(node, "module", getattr(node, "name", ""))
                iod_usage = getattr(node, "usage", "")
                iod_title_text = f"{iod_title} Module ({iod_usage})" if iod_usage else iod_title
                # Set title style
                row_style = (
                    "magenta" if colorize else None
                )
                table.add_row(iod_title_text, *[""] * (len(attr_headers) - 1), style=row_style)
            # Print module attribute nodes as regular rows
            else:
                row = [getattr(node, attr, "") for attr in self.model.metadata.column_to_attr.values()]
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