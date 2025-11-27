"""Printer class for DICOM IOD specification model in dcmspec.

Provides the SpecPrinter class for printing DICOM IOD specification models (SpecModel)
to standard output, either as a hierarchical tree or as a flat table, using rich formatting.
"""
import re
from typing import Generator, List, Optional, Tuple

from anytree import PreOrderIter
from anytree import RenderTree
from rich.table import Table, box
from rich.text import Text

from dcmspec.spec_printer import LEVEL_COLORS, SPECIAL_COLORS, SpecPrinter

class IODSpecPrinter(SpecPrinter):
    """Printer for DICOM IOD specification models with mixed node types.

    Overrides print_table to display IOD Modules nodes as a one-cell title row (spanning all columns)
    The table columns are those of the Module Attributes nodes.
    """

    def print_tree(
        self,
        attr_names=None,
        attr_widths=None,
        colorize: bool = False,
    ) -> None:
        """Print the specification model as a hierarchical tree to the console or file.

        Args:
            attr_names (Optional[Union[str, list[str]]]): Attribute name(s) to display for each node.
            attr_widths (Optional[list[int]]): List of widths for each attribute in attr_names.
            colorize (bool): Whether to colorize the output by node depth. Ignored when writing to file.

        Returns:
            None

        """
        if self.output:
            colorize = False

        for pre, fill, node in RenderTree(self.model.content):
            if node.name == "content":
                continue

            if hasattr(node, "module"):
                # Module title row: always use title color if colorize
                iod_title = getattr(node, "module", getattr(node, "name", ""))
                iod_usage = getattr(node, "usage", "")
                iod_title_text = f"{iod_title} Module ({iod_usage})" if iod_usage else iod_title
                node_text = Text(iod_title_text, style=SPECIAL_COLORS["title"] if colorize else None)
            else:
                attr_text = self._format_tree_row(node, attr_names, attr_widths)
                row_style = self._get_tree_row_style(node, colorize)
                node_text = Text(attr_text, style=row_style)
            self.console.print(Text(pre) + node_text)

        if self.console.file:
            self.console.file.flush()

    def print_table(self, column_widths=None, colorize: bool = False) -> None:
        """Print the specification model as a flat table with module title rows.

        Args:
            column_widths (Optional[List[int]]): List of widths for each column's content.
                These widths do not include borders or padding added by Rich.
                If provided, each column will be set to the specified content width.
                If None, all columns default to width 20.            
                If the list is shorter than the number of columns, remaining columns default to width 20.

            colorize (bool): Whether to colorize the output by node depth.

        """
        # Disable colorization if writing to file
        if self.output:
            colorize = False

        table = Table(show_header=True, header_style="bold magenta", show_lines=True, box=box.ASCII_DOUBLE_HEAD)

        attr_headers = list(self.model.metadata.header)
        for i, header in enumerate(attr_headers):
            width = column_widths[i] if column_widths and i < len(column_widths) else 20
            table.add_column(header, width=width)

        for row, row_style, _ in self._iterate_rows_iod(colorize):
            table.add_row(*row, style=row_style)

        self.console.print(table)

        if self.console.file:
            self.console.file.flush()  # Ensure data is written immediately

    def print_csv(self, colorize: bool = False) -> None:
        """Print the specification model as CSV to the console or file, with module title rows.

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

        # Add data rows (including module title rows)
        for row, row_style, _ in self._iterate_rows_iod(colorize):
            # Escape quotes inside each field by doubling them, then wrap in quotes
            csv_row = ",".join(
                f'"{("" if cell is None else str(cell)).replace(chr(34), chr(34) + chr(34))}"'
                for cell in row
            )
            self.console.print(csv_row, style=row_style)

        if self.console.file:
            self.console.file.flush()

    def print_xlsx(self, column_widths: Optional[list] = None, colorize: bool = False) -> None:
        """Print the specification model to an OOXML format Excel (.xlsx) file.

        Traverses the content tree and writes each node's attributes into an Excel sheet,
        with column headers from the metadata node. Handles newlines and applies background
        colorization using the same color scheme as console output (LEVEL_COLORS and SPECIAL_COLORS).
        Each module in the IOD is written to a separate worksheet, named after the module, and attribute rows
        for each module are written to their corresponding worksheet.

        Args:
            column_widths (list): Optional list of column widths for Excel columns.
            colorize (bool): Whether to apply color styling to cell backgrounds.

        Returns:
            None

        """
        if not self.output:
            raise ValueError("Output file path must be specified when constructing SpecPrinter for print_xlsx).")

        header_style, data_style = self._create_styles()
        wb = self._setup_workbook()
        ws = None
        current_module = None
        rows_for_ws = []

        def flush_ws():
            if ws and rows_for_ws:
                self._write_data_rows(ws, rows_for_ws, data_style, colorize)
                rows_for_ws.clear()

        used_names = set()
        for row, row_style, module_name in self._iterate_rows_iod(colorize=colorize, include_module_titles=False):
            if module_name != current_module:
                flush_ws()
                
                ws = self._setup_worksheet(wb, self._sanitize_sheet_name(module_name, used_names))
                self._write_headers(ws, self.model.metadata.header, header_style)
                if column_widths:
                    self._set_column_widths(ws, column_widths)
                current_module = module_name
            rows_for_ws.append((row, row_style))

        flush_ws()
        wb.save(self.output)
        
    @staticmethod
    def _sanitize_sheet_name(name: str, used_names: set = None) -> str:
        """Sanitize and ensure uniqueness of a worksheet name for Excel compatibility.

        This function replaces invalid characters with underscores and trims the name to 31 characters.
        If the name is empty or None, it uses 'Sheet'. If the name is already used, it appends a numeric
        suffix to ensure uniqueness within the workbook.

        Args:
            name (str): The proposed worksheet name.
            used_names (set, optional): Set of already used worksheet names.

        Returns:
            str: A sanitized and unique worksheet name suitable for Excel.

        """
        orig_name = re.sub(r'[\[\]\*:/\\\?]', '_', name) if name else "Sheet"
        orig_name = orig_name[:31] if orig_name else "Sheet"
        if used_names is None:
            used_names = set()
        sheet_name = orig_name
        i = 1
        while sheet_name in used_names or not sheet_name:
            suffix = f"_{i}"
            sheet_name = (
                (orig_name[:31-len(suffix)] + suffix) 
                if len(orig_name) + len(suffix) > 31 
                else orig_name + suffix
            )
            i += 1
        used_names.add(sheet_name)
        return sheet_name

    def _iterate_rows_iod(
            self, 
            colorize: bool = False, 
            include_module_titles: bool = True
            ) -> Generator[Tuple[List[str], Optional[str], Optional[str]], None, None]:
        """Generate rows for IODSpecPrinter with module title rows, module grouping, and optional styling.

        Iterates through the model content tree and yields tuples representing each row to be printed.
        For module nodes, optionnaly yields a module title row with the module name and styling.
        For attribute rows, yields the attribute values, row style, and the current module name for grouping.

        Args:
            colorize (bool): Whether to apply color styling to rows.
            include_module_titles (bool): Whether to yield module title rows (True for table/csv, False for xlsx).

        Yields:
            tuple: (row_data, row_style, module_name) where row_data is a list of cell values,
                    row_style is an RGB color string (e.g., "rgb(255,255,0)") from LEVEL_COLORS or SPECIAL_COLORS,
                    or None if not colorized, and module_name is the current module for grouping.

        """      
        attr_headers = list(self.model.metadata.header)
        current_module = None
        for node in PreOrderIter(self.model.content):
            if node.name == "content":
                continue
            if hasattr(node, "module"):
                current_module = getattr(node, "module", None)
                if include_module_titles:
                    iod_title = getattr(node, "module", getattr(node, "name", ""))
                    iod_usage = getattr(node, "usage", "")
                    iod_title_text = f"{iod_title} Module ({iod_usage})" if iod_usage else iod_title
                    row_style = SPECIAL_COLORS["title"] if colorize else None
                    yield [iod_title_text] + [""] * (len(attr_headers) - 1), row_style, current_module or "Other"
                # else: skip module title rows for xlsx
            else:
                # Use the most recent current_ie for all attribute rows
                row = [getattr(node, attr, "") for attr in self.model.metadata.column_to_attr.values()]
                row_style = None
                if colorize:
                    if self.model._is_include(node):
                        row_style = SPECIAL_COLORS["include"]
                    elif self.model._is_title(node):
                        row_style = SPECIAL_COLORS["title"]
                    else:
                        # use (node.depth - 2) since attributes are children of module nodes,
                        # which are themselves children of content (root) node
                        row_style = LEVEL_COLORS[(node.depth - 2) % len(LEVEL_COLORS)]
                yield row, row_style, current_module or "Other"