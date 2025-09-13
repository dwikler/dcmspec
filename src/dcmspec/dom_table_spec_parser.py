"""DOM specification parser class for DICOM standard processing in dcmspec.

Provides the DOMSpecParser class for parsing DICOM specification tables from XHTML documents,
converting them into structured in-memory representations using anytree.
"""
from contextlib import contextmanager
import re
import unicodedata
from unidecode import unidecode
from anytree import Node
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, Optional, Union
from dcmspec.spec_parser import SpecParser

from dcmspec.dom_utils import DOMUtils
from dcmspec.progress import Progress, ProgressStatus, calculate_percent

class DOMTableSpecParser(SpecParser):
    """Parser for DICOM specification tables in XHTML DOM format.

    Provides methods to extract, parse, and structure DICOM specification tables from XHTML documents,
    returning anytree Node objects as structured in-memory representations.
    Inherits logging from SpecParser.
    """

    def __init__(self, logger: Optional[Any] = None):
        """Initialize the DOMTableSpecParser.

        Sets up the parser with an optional logger and a DOMUtils instance for DOM navigation.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        super().__init__(logger=logger)

        self.dom_utils = DOMUtils(logger=self.logger)

    def parse(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
        name_attr: str,
        include_depth: Optional[int] = None,  # None means unlimited
        progress_observer: Optional[Any] = None,
        skip_columns: Optional[list[int]] = None,
        unformatted: Optional[Union[bool, Dict[int, bool]]] = True,
    ) -> tuple[Node, Node]:
        """Parse specification metadata and content from tables in the DOM.

        Parses tables within the DOM of a DICOM document and returns a tuple containing
        the metadata node and the table content node as structured in-memory representations.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            table_id (str): The ID of the table to parse.
            column_to_attr (Dict[int, str]): Mapping from column indices to attribute names for tree nodes.
            name_attr (str): The attribute name to use for building node names.
            include_depth (Optional[int], optional): The depth to which included tables should be parsed. 
                None means unlimited.
            progress_observer (Optional[object], optional): Optional observer to report download progress.
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a column.
                This argument is typically set via `parser_kwargs` when using SpecFactory.
            unformatted (Optional[Union[bool, Dict[int, bool]]]): 
                Whether to extract unformatted (plain text) cell content (default True).
                Can be a bool (applies to all columns) or a dict mapping column indices to bools.
                This argument is typically set via `parser_kwargs` when using SpecFactory.

        Returns:
            Tuple[Node, Node]: The metadata node and the table content node.

        """
        self._skipped_columns_flag = False

        # Build a list of booleans indicating, for each column, whether to extract its cells as unformatted text.
        # Default is True (extract as unformatted text) for all columns.
        num_columns = max(column_to_attr.keys()) + 1
        if isinstance(unformatted, dict):
            unformatted_list = [unformatted.get(i, True) for i in range(num_columns)]
        else:
            unformatted_list = [unformatted] * num_columns

        content = self.parse_table(
            dom, 
            table_id, 
            column_to_attr, 
            name_attr, 
            include_depth=include_depth, 
            progress_observer=progress_observer,
            skip_columns=skip_columns, 
            unformatted_list=unformatted_list
        )

        # If we ever skipped columns, remove them from metadata.column_to_attr and realign keys
        if skip_columns and self._skipped_columns_flag:
            kept_items = [(k, v) for k, v in column_to_attr.items() if k not in skip_columns]
            filtered_column_to_attr = {i: v for i, (k, v) in enumerate(kept_items)}
        else:
            filtered_column_to_attr = column_to_attr

        metadata = self.parse_metadata(dom, table_id, filtered_column_to_attr)
        metadata.column_to_attr = filtered_column_to_attr
        metadata.table_id = table_id
        if include_depth is not None:
            metadata.include_depth = int(include_depth)
        return metadata, content

    @contextmanager
    def _visit_table(self, table_id: str, visited_tables: set) -> Any:
        """Context manager to temporarily add a table_id to the visited_tables set during recursion.

        Ensures that table_id is added to visited_tables when entering the context,
        and always removed when exiting, even if an exception occurs.

        Args:
            table_id: The ID of the table being visited.
            visited_tables: The set of table IDs currently being visited in the recursion stack.

        """
        visited_tables.add(table_id)
        try:
            yield
        finally:
            visited_tables.remove(table_id)

    def parse_table(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int = 0,
        include_depth: Optional[int] = None,  # None means unlimited
        progress_observer: Optional[Any] = None,
        skip_columns: Optional[list[int]] = None,
        visited_tables: Optional[set] = None,
        unformatted_list: Optional[list[bool]] = None,
    ) -> Node:
        """Parse specification content from tables within the DOM of a DICOM document.

        This method extracts data from each row of the table, handles nested
        tables indicated by "Include" links, and builds a tree-like structure
        of the DICOM attributes which root node is assigned to the attribute
        model.

        Args:
            dom: The BeautifulSoup DOM object.
            table_id: The ID of the table to parse.
            column_to_attr: Mapping between index of columns to parse and tree nodes attributes names
            name_attr: tree node attribute name to use to build node name
            table_nesting_level: The nesting level of the table (used for recursion call only).
            include_depth: The depth to which included tables should be parsed.
            progress_observer (Optional[object], optional): Optional observer to report download progress.
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a column.
            visited_tables (Optional[set]): Set of table IDs that have been visited to prevent infinite recursion.
            unformatted_list (Optional[list[bool]]): List of booleans indicating whether to extract each column as 
                unformatted text.

        Returns:
            root: The root node of the tree representation of the specification table.

        """
        self.logger.info(f"Nesting Level: {table_nesting_level}, Parsing table with id {table_id}")

        if unformatted_list is None:
            num_columns = max(column_to_attr.keys()) + 1
            unformatted_list = [True] * num_columns

        self._enforce_unformatted_for_name_attr(column_to_attr, name_attr, unformatted_list)

        # Initialize visited_tables set if not provided (first call)
        if visited_tables is None:
            visited_tables = set()

        # Use a context manager to ensure table_id is always added to and removed from
        # visited_tables, even if an exception occurs.
        with self._visit_table(table_id, visited_tables):
            # Maps column indices in the DICOM standard table to corresponding node attribute names
            # for constructing a tree-like representation of the table's data.
            # self.column_to_attr = {**{0: "elem_name", 1: "elem_tag"}, **(column_to_attr or {})}

            table = self.dom_utils.get_table(dom, table_id)
            if not table:
                raise ValueError(f"Table with id '{table_id}' not found.")

            if not column_to_attr:
                raise ValueError("Columns to node attributes missing.")
            else:
                self.column_to_attr = column_to_attr

            root = Node("content")
            level_nodes: Dict[int, Node] = {0: root}


            self._process_table_rows(
                table=table,
                dom=dom,
                column_to_attr=column_to_attr,
                name_attr=name_attr,
                table_nesting_level=table_nesting_level,
                include_depth=include_depth,
                skip_columns=skip_columns,
                visited_tables=visited_tables,
                unformatted_list=unformatted_list,
                level_nodes=level_nodes,
                root=root,
                progress_observer=progress_observer if table_nesting_level == 0 else None,
            )

            self.logger.info(f"Nesting Level: {table_nesting_level}, Table parsed successfully")

            return root

    def parse_metadata(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
    ) -> Node:
        """Parse specification metadata from the document and the table within the DOM of a DICOM document.

        This method extracts the version of the DICOM standard and the headers of the tables.

        Args:
            dom: The BeautifulSoup DOM object.
            table_id: The ID of the table to parse.
            column_to_attr: Mapping between index of columns to parse and attributes name.

        Returns:
            metadata_node: The root node of the tree representation of the specification metadata.

        """
        table = self.dom_utils.get_table(dom, table_id)
        if not table:
            raise ValueError(f"Table with id '{table_id}' not found.")

        metadata = Node("metadata")
        # Parse the DICOM Standard document information
        version = self.get_version(dom, table_id)
        metadata.version = version
        # Parse the Attribute table header
        header = self._extract_header(table, column_to_attr=column_to_attr)
        metadata.header = header

        return metadata

    def get_version(self, dom: BeautifulSoup, table_id: str) -> str:
        """Retrieve the DICOM Standard version from the DOM.

        Args:
            dom: The BeautifulSoup DOM object.
            table_id: The ID of the table to retrieve.

        Returns:
            info_node: The info tree node.

        """
        version = self._version_from_book(dom) or self._version_from_section(dom)
        if not version:
            version = ""
            self.logger.warning("DICOM Standard version not found")
        return version

    def _version_from_book(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract version of DICOM books in HTML format."""
        titlepage = dom.find("div", class_="titlepage")
        if titlepage:
            subtitle = titlepage.find("h2", class_="subtitle")
        return subtitle.text.split()[2] if subtitle else None

    def _version_from_section(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract version of DICOM sections in the CHTML format."""
        document_release = dom.find("span", class_="documentreleaseinformation")
        return document_release.text.split()[2] if document_release else None

    def _process_table_rows(
        self,
        table: Tag,
        dom: BeautifulSoup,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int,
        include_depth: Optional[int],
        skip_columns: Optional[list[int]],
        visited_tables: set,
        unformatted_list: list[bool],
        level_nodes: Dict[int, Node],
        root: Node,
        progress_observer: Optional[Any] = None
    ) -> None:
        """Process all rows in the table, handling recursion, nesting, and node creation."""
        rows = table.find_all("tr")[1:]
        total_rows = len(rows)
        for idx, row in enumerate(rows):
            row_data = self._extract_row_data(row, skip_columns=skip_columns, unformatted_list=unformatted_list)
            if row_data[name_attr] is None:
                continue  # Skip empty rows
            row_nesting_level = table_nesting_level + row_data[name_attr].count(">")

            # Add nesting level symbols to included table element names except if row is a title
            if table_nesting_level > 0 and not row_data[name_attr].isupper():
                row_data[name_attr] = ">" * table_nesting_level + row_data[name_attr]

            # Process Include statement unless include_depth is defined and not reached
            if "Include" in row_data[name_attr] and (include_depth is None or include_depth > 0):
                next_depth = None if include_depth is None else include_depth - 1

                should_include = self._check_circular_reference(row, visited_tables, table_nesting_level)
                if should_include:
                    self._parse_included_table(
                        dom, row, column_to_attr, name_attr, row_nesting_level, next_depth,
                        level_nodes, root, visited_tables, unformatted_list
                    )
                else:
                    # Create a node to represent the circular reference instead of recursing
                    node_name = self._sanitize_string(row_data[name_attr])
                    self._create_node(node_name, row_data, row_nesting_level, level_nodes, root)
            else:
                node_name = self._sanitize_string(row_data[name_attr])
                self._create_node(node_name, row_data, row_nesting_level, level_nodes, root)
            # Only report progress for the root table
            if progress_observer is not None:
                percent = calculate_percent(idx + 1, total_rows)
                progress_observer(Progress(
                    percent,
                    status=ProgressStatus.PARSING_TABLE,
                ))

    def _extract_row_data(
        self,
        row: Tag,
        skip_columns: Optional[list[int]] = None,
        unformatted_list: Optional[list[bool]] = None
    ) -> Dict[str, Any]:
        """Extract data from a table row.

        Processes each cell in the row, accounting for colspans and rowspans and extract formatted (HTML)
        or unformatted value from paragraphs within the cells.
        Constructs a dictionary containing the extracted values for each logical column requested by the parser
        (each column defined in `self.column_to_attr`).

        If, after accounting for colspans and rowspans, the row has one fewer value than the number of logical columns
        in the mapping and if skip_columns is set, those columns will be skipped for this row, allowing for robust
        alignment when Module Tables and nested Attributes Tables may not have the same number of columns as it may be
        for normalized IOD Modules.

        Args:
            row: The table row element (BeautifulSoup Tag for <tr> element).
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a logical column.
            unformatted_list (Optional[list[bool]]): List of booleans indicating whether to extract each column value as
                unformatted (HTML) or formatted (ASCII) data.

        Returns:
            Dict[str, Any]: A dictionary mapping attribute names to cell values of the logical columns for the row.

            - The **key** is the attribute name as defined in `self.column_to_attr` 
                (e.g., "ie", "module", "ref", "usage").
            - The **value** is the cell value for that column in this row, which may be:
                - The value physically present in the current row,
                - Or a value carried over from a previous row due to rowspan.

        """
        # Initialize rowspan trackers if not present
        if not hasattr(self, "_rowspan_trackers") or self._rowspan_trackers is None:
            self._rowspan_trackers = []

        num_logical_columns = len(self.column_to_attr)  # Number of logical columns, hence expected number of cells
        logical_cells = []  # List to hold the logical cell values
        logical_col_idx = 0  # Logical column index in the table, index of the attribute in column_to_attr, 0-based
        physical_col_idx = 0  # Physical column index in the DOM, index of the <td> cell in the <tr>, 0-based

        # Iterator for the <td> elements in the current row
        cell_iter = iter(row.find_all("td"))
        num_physical_cells = len(row.find_all("td"))

        # Only apply skip_columns if the row is missing exactly that many columns
        apply_skip = (
            skip_columns
            and num_physical_cells == num_logical_columns - len(skip_columns)
        )

        # 1. Handle carried-forward cells from rowspans
        logical_cells, logical_col_idx, physical_col_idx = self._handle_rowspan_cells(
            logical_cells, logical_col_idx, physical_col_idx, num_logical_columns
        )

        # 2. Process each logical column in the row, extracting values from physical <td> cells
        while logical_col_idx < num_logical_columns:
            # Skip this logical column if requested and missing in the row
            if apply_skip and logical_col_idx in skip_columns:
                logical_col_idx += 1
                continue

            logical_cells, logical_col_idx, physical_col_idx = self._process_logical_column(
                cell_iter, logical_cells, logical_col_idx, physical_col_idx, skip_columns, unformatted_list
            )

        # 3. Trim _rowspan_trackers to match the number of physical columns in this row
        if len(self._rowspan_trackers) > physical_col_idx:
            self._rowspan_trackers = self._rowspan_trackers[:physical_col_idx]

        # 4. Map logical cells to attributes, omitting skipped columns if missing in the row
        attr_indices = list(self.column_to_attr.keys())
        if skip_columns and len(logical_cells) == len(self.column_to_attr) - len(skip_columns):
            return self._map_cells_with_skipped_columns(
                logical_cells, attr_indices, skip_columns
            )
        else:
            return self._map_cells_to_attributes(logical_cells, attr_indices)
    

    def _handle_rowspan_cells(
        self,
        logical_cells: list,
        logical_col_idx: int,
        physical_col_idx: int,
        num_logical_columns: int
    ) -> tuple[list, int, int]:
        """Handle carried-forward cells from rowspans for the current row.

        For each logical column, if a rowspan tracker is active for the current physical column,
        use its carried-forward value for this logical column.
        Advances logical and physical indices as needed.

        Returns:
            tuple: (logical_cells, logical_col_idx, physical_col_idx)
                - logical_cells: The updated list of extracted cell values for the row.
                - logical_col_idx: The next logical column index to process.
                - physical_col_idx: The next physical column index to process.

        """
        while (
            physical_col_idx < len(self._rowspan_trackers)
            and logical_col_idx < num_logical_columns
            and self._rowspan_trackers[physical_col_idx]
            and self._rowspan_trackers[physical_col_idx]["rows_left"] > 0
        ):
            # Use carried-forward value for this logical column
            value = self._rowspan_trackers[physical_col_idx]["value"]
            logical_cells.append(value)
            self._rowspan_trackers[physical_col_idx]["rows_left"] -= 1

        # Advance to next logical column and past all physical columns spanned by the carried-forward cell
            physical_col_idx += self._rowspan_trackers[physical_col_idx]["colspan"]
            logical_col_idx += 1

        return logical_cells, logical_col_idx, physical_col_idx


    def _process_logical_column(
        self,
        cell_iter: Any,
        logical_cells: list,
        logical_col_idx: int,
        physical_col_idx: int,
        skip_columns: Optional[list[int]],
        unformatted_list: Optional[list[bool]]
    ) -> tuple[list, int, int]:
        """Process a single logical column in the row.

        Extract the value from the corresponding physical <td> cell (if present),
        handle colspans and rowspans, and update logical and physical indices.

        Returns:
            tuple: (logical_cells, logical_col_idx, physical_col_idx)
                - logical_cells: The updated list of extracted cell values for the row.
                - logical_col_idx: The next logical column index to process.
                - physical_col_idx: The next physical column index to process.

        """
        # Ensure _rowspan_trackers has an entry for this physical column
        if physical_col_idx >= len(self._rowspan_trackers):
            self._rowspan_trackers.append(None)

        # Ensure logical_cells has an entry for this logical column (fill with None if missing in DOM)
        try:
            cell = next(cell_iter)
        except StopIteration:
            logical_cells.append(None)
            logical_col_idx += 1
            return logical_cells, logical_col_idx, physical_col_idx

        # Extract value for the current logical column using the specified unformatted setting
        value = self._extract_cell_value(cell, logical_col_idx, unformatted_list)

        # Determine colspan and rowspan
        colspan = int(cell.get("colspan", 1))
        rowspan = int(cell.get("rowspan", 1))

        # Add the value for the first logical column spanned by this cell
        logical_cells.append(value)
        # Add None for each additional logical column spanned by colspan, unless skipped
        logical_cells.extend(
            None
            for j in range(1, colspan)
            if not skip_columns or logical_col_idx + j not in skip_columns
        )
        
        # Update rowspan tracker for each physical column spanned by this cell
        self._update_rowspan_trackers(physical_col_idx, colspan, rowspan, value)

        # Advance logical and physical column indices by colspan
        physical_col_idx += colspan
        logical_col_idx += colspan

        return logical_cells, logical_col_idx, physical_col_idx

    def _extract_cell_value(
        self,
        cell: Tag,
        logical_col_idx: int,
        unformatted_list: list[bool]
    ) -> str:
        """Extract and clean the value from a cell as unformatted text or HTML."""
        use_unformatted = (
            unformatted_list[logical_col_idx]
            if unformatted_list and logical_col_idx < len(unformatted_list)
            else True
        )
        if use_unformatted:
            return self._clean_extracted_text(cell.get_text(separator="\n", strip=True))
        else:
            return self._clean_extracted_text(cell.decode_contents())

    def _update_rowspan_trackers(
        self,
        physical_col_idx: int,
        colspan: int,
        rowspan: int,
        value: Any
    ) -> None:
        """Update the rowspan tracker for each physical column spanned by the cell."""
        for i in range(colspan):
            while len(self._rowspan_trackers) <= physical_col_idx + i:
                self._rowspan_trackers.append(None)
            if rowspan > 1:
                value_for_tracker = value if i == 0 else None
                self._rowspan_trackers[physical_col_idx + i] = {
                    "value": value_for_tracker,
                    "rows_left": rowspan - 1,
                    "colspan": 1,
                }
            else:
                self._rowspan_trackers[physical_col_idx + i] = None

    def _map_cells_with_skipped_columns(
        self,
        cells: list,
        attr_indices: list[int],
        skip_columns: list[int]
    ) -> dict:
        """Map the list of extracted cell values to the attribute names for this row in presence of skipped columns.

        This method is used when skip_columns is set and the number of logical cells
        matches the expected number of non-skipped columns. It ensures that only the
        non-skipped attributes are present in the output dictionary.

        Args:
            cells (list): Extracted cell values for the row, in logical column order (excluding skipped columns).
            attr_indices (list): Column indices (keys from column_to_attr) in logical order.
            skip_columns (list): Column indices to skip.

        Returns:
            dict: Dictionary mapping attribute names to cell values (excluding skipped columns).
            
        """
        attr_indices = [i for i in attr_indices if i not in skip_columns]

        # Flag if the skipped_columns were actually skipped
        self._skipped_columns_flag = True

        # Map the remaining cells to the correct attributes
        return {
            self.column_to_attr[attr_indices[attr_index]]: cell
            for attr_index, cell in enumerate(cells)
            if attr_index < len(attr_indices)
        }

    def _map_cells_to_attributes(
        self,
        cells: list,
        attr_indices: list[int]
    ) -> dict:
        """Map the list of extracted cell values to the attribute names for this row.

        This method builds a dictionary mapping each attribute name (from column_to_attr)
        to the corresponding value in the `cells` list. If there are fewer cells than attributes,
        the remaining attributes are filled with None.

        Args:
            cells (list): List of extracted cell values for the row, in logical column order.
            attr_indices (list): List of column indices (keys from column_to_attr) in logical order.

        Returns:
            dict: Dictionary mapping attribute names to cell values (or None if missing).

        """
        row_data = {}
        attr_indices = sorted(attr_indices)
        for i, attr_idx in enumerate(attr_indices):
            attr = self.column_to_attr[attr_idx]
            row_data[attr] = cells[i] if i < len(cells) else None
        return row_data
    
    def _handle_pending_rowspans(self) -> tuple[list, list, list, int, int]:
        """Handle cells that are carried forward from previous rows due to rowspan.

        This method checks the internal _rowspan_trackers for any cells that are being
        carried forward from previous rows (i.e., have rows_left > 0). For each such cell,
        it appends the carried-forward value to the current row's cell list, and updates
        the physical and logical column indices accordingly.

        Returns:
            tuple: (cells, colspans, rowspans, physical_col_idx, logical_col_idx)
                - cells: list of carried-forward cell values for this row
                - colspans: list of colspans for each carried-forward cell
                - rowspans: list of remaining rowspans for each carried-forward cell
                - physical_col_idx: the next available physical column index in the row
                - logical_col_idx: the next available logical column index in the row

        Note:
            - physical_col_idx tracks the actual position in the HTML table, including colspans.
            - logical_col_idx tracks the logical data model column, incremented by 1 per cell.

        """
        cells = []
        colspans = []
        rowspans = []
        physical_col_idx = 0
        logical_col_idx = 0

        for tracker in self._rowspan_trackers:
            if tracker and tracker["rows_left"] > 0:
                cells.append(tracker["value"])
                colspans.append(tracker["colspan"])
                rowspans.append(tracker["rows_left"])
                tracker["rows_left"] -= 1
                physical_col_idx += tracker["colspan"]
                logical_col_idx += 1

        return cells, colspans, rowspans, physical_col_idx, logical_col_idx

    def _enforce_unformatted_for_name_attr(
        self,
        column_to_attr: dict[int, str],
        name_attr: str,
        unformatted_list: list[bool]
    ) -> None:
        """Enforce unformatted=True for the name_attr column if it is not already set."""
        name_attr_col = next((col_idx for col_idx, attr in column_to_attr.items() if attr == name_attr), None)
        if name_attr_col is not None and not unformatted_list[name_attr_col]:
            unformatted_list[name_attr_col] = True
            if self.logger:
                self.logger.warning(
                    f"unformatted=False for name_attr column '{name_attr}' (index {name_attr_col}) is not allowed. "
                    "Forcing unformatted=True for this column to ensure correct parsing."
                )

    def _check_circular_reference(
        self,
        row: Tag,
        visited_tables: set,
        table_nesting_level: int
    ) -> bool:
        """Check for circular reference before attempting to parse an included table.

        Returns:
            bool: True if the table should be included (no circular reference), False otherwise.

        """
        include_anchor = row.find("a", {"class": "xref"})
        if include_anchor:
            include_table_id = include_anchor["href"].split("#", 1)[-1]
            if include_table_id in visited_tables:
                self.logger.warning(
                    f"Nesting Level: {table_nesting_level}, Circular reference detected for "
                    f"table {include_table_id}, creating node instead of recursing"
                )
                return False
        return True

    def _parse_included_table(
        self,
        dom: BeautifulSoup,
        row: Tag,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int,
        include_depth: int,
        level_nodes: Dict[int, Node],
        root: Node,
        visited_tables: set,
        unformatted_list: Optional[list[bool]] = None
    ) -> None:
        """Recursively parse Included Table."""
        include_anchor = row.find("a", {"class": "xref"})
        if not include_anchor:
            self.logger.warning(f"Nesting Level: {table_nesting_level}, Include Table Id not found")
            return

        include_table_id = include_anchor["href"].split("#", 1)[-1]
        self.logger.debug(f"Nesting Level: {table_nesting_level}, Include Table Id: {include_table_id}")

        included_table_tree = self.parse_table(
            dom,
            include_table_id,
            column_to_attr=column_to_attr,
            name_attr=name_attr,
            table_nesting_level=table_nesting_level,
            include_depth=include_depth,
            visited_tables=visited_tables,
            unformatted_list=unformatted_list
        )
        if not included_table_tree:
            return

        self._nest_included_table(included_table_tree, level_nodes, table_nesting_level, root)

    def _nest_included_table(
        self,
        included_table_tree: Node,
        level_nodes: Dict[int, Node],
        row_nesting_level: int,
        root: Node
    ) -> None:
        """Nest the included table tree under the appropriate parent node."""
        parent_node = level_nodes.get(row_nesting_level - 1, root)
        for child in included_table_tree.children:
            child.parent = parent_node

    def _create_node(
        self,
        node_name: str,
        row_data: Dict[str, Any],
        row_nesting_level: int,
        level_nodes: Dict[int, Node],
        root: Node
    ) -> None:
        """Create a new node and attach it to the appropriate parent."""
        parent_node = level_nodes.get(row_nesting_level - 1, root)
        self.logger.debug(
            f"Nesting Level: {row_nesting_level}, Name: {node_name}, "
            f"Parent: {parent_node.name if parent_node else 'None'}"
        )
        node = Node(node_name, parent=parent_node, **row_data)
        level_nodes[row_nesting_level] = node

    def _extract_header(
        self,
        table: Tag,
        column_to_attr: Dict[int, str]
    ) -> list[str]:
        """Extract headers from the table and saves them in the headers attribute.

        Realign the keys in column_to_attr to consecutive indices if the number of columns in the table
        is less than the maximum key in column_to_attr, to handle cases where the mapping is out of sync
        with the actual table structure.

        Args:
            table: The table element from which to extract headers.
            column_to_attr: Mapping between index of columns to parse and attributes name. 

        """
        cells = table.find_all("th")
        num_columns = len(cells)
        # If the mapping has non-consecutive keys and the table has fewer columns, realign
        if max(column_to_attr.keys()) >= num_columns:
            # Map consecutive indices to the same attribute names, skipping as needed
            sorted_attrs = [column_to_attr[k] for k in sorted(column_to_attr.keys())]
            realigned_col_to_attr = dict(enumerate(sorted_attrs))
            column_to_attr = realigned_col_to_attr

        header = []
        header.extend(
            cells[col_idx].get_text(strip=True)
            for col_idx in column_to_attr
            if col_idx < len(cells)
        )
        self.logger.info(f"Extracted Header: {header}")
        return header

    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text using Unicode normalization and regex.

        Args:
            text (str): The text to be cleaned.

        Returns:
            str: The cleaned text.

        """
        # Normalize unicode characters to compatibility form
        cleaned = unicodedata.normalize('NFKC', text)

        # Replace non-breaking spaces and zero-width spaces with regular space
        cleaned = re.sub(r'[\u00a0\u200b]', ' ', cleaned)

        # Replace typographic single quotes with ASCII single quote
        cleaned = re.sub(r'[\u2018\u2019]', "'", cleaned)
        # Replace typographic double quotes with ASCII double quote
        cleaned = re.sub(r'[\u201c\u201d\u00e2\u0080\u009c\u00e2\u0080\u009d]', '"', cleaned)
        # Replace em dash and en dash with hyphen
        cleaned = re.sub(r'[\u2013\u2014]', '-', cleaned)
        # Remove stray Â character
        cleaned = cleaned.replace('\u00c2', '')

        return cleaned.strip()

    def _sanitize_string(self, input_string: str) -> str:
        """Sanitize string to use it as a node attribute name.

        - Convert non-ASCII characters to closest ASCII equivalents
        - Replace space characters and slashes with underscores
        - Replace parentheses characters with dashes

        Args:
            input_string (str): The string to be sanitized.

        Returns:
            str: The sanitized string.

        """
        # Normalize the string to NFC form and transliterate to ASCII
        normalized_str = unidecode(input_string.lower())
        # Replace spaces and slashes with underscores, parentheses with dashes, and single quotes with underscores
        return re.sub(
            r"[ /\-()']",
            lambda match: "-" if match.group(0) in "()" else "_",
            normalized_str,
        )
