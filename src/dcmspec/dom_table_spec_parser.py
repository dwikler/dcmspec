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

    def __init__(self, logger=None):
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
        progress_observer: Optional[object] = None,        
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
    def _visit_table(self, table_id, visited_tables):
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
        progress_observer: Optional[object] = None,
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

    def _version_from_book(self, dom):
        """Extract version of DICOM books in HTML format."""
        titlepage = dom.find("div", class_="titlepage")
        if titlepage:
            subtitle = titlepage.find("h2", class_="subtitle")
        return subtitle.text.split()[2] if subtitle else None

    def _version_from_section(self, dom):
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
        progress_observer: Optional[object] = None
    ):
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
        alignment when a column is sometimes missing such as in the case of some of the Modules of a normalized IOD.

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

            This ensures that each row's dictionary contains values for all requested logical columns, regardless of
            whether the value is physically present in the current row or carried forward from a previous row due to
            rowspan. The result is a complete, logically-aligned mapping for each row in the table.

        """
        # Initialize rowspan trackers if not present
        if not hasattr(self, "_rowspan_trackers") or self._rowspan_trackers is None:
            self._rowspan_trackers = []

        # Add cells from pending rowspans
        cells, colspans, rowspans, physical_col_idx, logical_col_idx = self._handle_pending_rowspans()

        attr_indices = list(self.column_to_attr.keys())

        # Process the actual cells in this row, using skip_columns to align indices
        physical_col_idx = self._process_actual_cells(
            row,
            cells,
            colspans,
            rowspans,
            physical_col_idx,
            unformatted_list,
            skip_columns=skip_columns,
            logical_col_idx=logical_col_idx
        )

        # Clean up rowspan trackers for cells that are no longer needed
        if len(self._rowspan_trackers) > physical_col_idx:
            self._rowspan_trackers = self._rowspan_trackers[:physical_col_idx]

        return (
            self._align_row_with_skipped_columns(
                cells, colspans, attr_indices, skip_columns
            )
            if skip_columns
            and len(cells) == len(self.column_to_attr) - len(skip_columns)
            else self._align_row_default(cells, colspans, attr_indices)
        )
    
    def _align_row_with_skipped_columns(
        self, cells, colspans, attr_indices, skip_columns
    ):
        """Align cells to attributes when skip_columns is used.

        This method aligns the row's cells to the attribute indices, skipping the columns
        specified in skip_columns. It is used when the row is missing exactly the number of
        columns specified, ensuring the remaining cells are mapped to the correct attributes.

        """
        attr_indices = [i for i in attr_indices if i not in skip_columns]

        # Flag if the skipped_columns were actually skipped
        self._skipped_columns_flag = True

        # Map the remaining cells to the correct attributes
        return {
            self.column_to_attr[attr_indices[attr_index]]: cell
            for attr_index, (cell, colspan) in enumerate(zip(cells, colspans))
            if attr_index < len(attr_indices)
        }

    def _align_row_default(self, cells, colspans, attr_indices):
        """Align cells to attributes by default, handling colspans and missing cells.
        
        Always set all attributes, even if missing in this row, filling spanned columns with None
        to maintain alignment with the column_to_attr mapping.
        
        """
        row_data = {}
        cell_idx = 0
        attr_indices = sorted(attr_indices)
        i = 0
        while i < len(attr_indices):
            attr = self.column_to_attr[attr_indices[i]]
            if cell_idx < len(cells):
                row_data[attr] = cells[cell_idx]
                colsp = colspans[cell_idx] if cell_idx < len(colspans) else 1
                # Fill in None for skipped columns due to colspan
                for _ in range(1, colsp):
                    i += 1
                    if i < len(attr_indices):
                        skipped_attr = self.column_to_attr[attr_indices[i]]
                        row_data[skipped_attr] = None
                cell_idx += 1
            else:
                row_data[attr] = None
            i += 1
        return row_data
    
    def _handle_pending_rowspans(self):
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

    def _enforce_unformatted_for_name_attr(self, column_to_attr, name_attr, unformatted_list):
        name_attr_col = next((col_idx for col_idx, attr in column_to_attr.items() if attr == name_attr), None)
        if name_attr_col is not None and not unformatted_list[name_attr_col]:
            unformatted_list[name_attr_col] = True
            if self.logger:
                self.logger.warning(
                    f"unformatted=False for name_attr column '{name_attr}' (index {name_attr_col}) is not allowed. "
                    "Forcing unformatted=True for this column to ensure correct parsing."
                )

    def _process_actual_cells(
        self,
        row,
        cells,
        colspans,
        rowspans,
        physical_col_idx,
        unformatted_list,
        skip_columns=None,
        logical_col_idx=0
    ):
        """Process the actual (non-rowspan) cells in a table row, extracting text or HTML as needed.

        The "actual (non-rowspan) cells" are the BeautifulSoup Tag objects for <td> elements
        that are physically present in the current row of the HTML table. These do not include
        cells that are logically present due to a rowspan from a previous row; those are handled
        separately by _handle_pending_rowspans.

        This method iterates through the logical columns of the row, skipping columns as specified,
        and for each column:
            - If a cell is present in the current row, extracts its value (as text or HTML depending on
                the boolean value in unformatted_list).
            - If a cell is carried forward due to rowspan, it is already handled by _handle_pending_rowspans.
            - Updates the physical and logical column indices as it processes each cell.

        Args:
            row: The BeautifulSoup Tag for the current table row.
            cells: List to append extracted cell values to.
            colspans: List to append colspans for each cell.
            rowspans: List to append rowspans for each cell.
            physical_col_idx: The current physical column index in the HTML table (including colspans).
            unformatted_list: List of booleans indicating whether to extract each column as unformatted text.
            skip_columns: Optional list of logical column indices to skip.
            logical_col_idx: The current logical column index in the data model (default 0).

        Returns:
            int: The updated physical_col_idx after processing all cells in the row.

        Note:
            - physical_col_idx tracks the actual position in the HTML table, including colspans.
            - logical_col_idx tracks the logical data model column, incremented by 1 per cell.
            - This method ensures correct alignment between the HTML table and the data model,
            even in the presence of rowspans and colspans.

        """
        cell_iter = iter(row.find_all("td"))
        num_columns = len(unformatted_list)
        while logical_col_idx < num_columns:
            # Skip columns as needed
            if skip_columns and logical_col_idx in skip_columns:
                logical_col_idx += 1
                continue

            if physical_col_idx >= len(self._rowspan_trackers):
                self._rowspan_trackers.append(None)

            try:
                cell = next(cell_iter)
            except StopIteration:
                # If we run out of cells, fill the rest with None
                cells.append(None)
                colspans.append(1)
                rowspans.append(1)
                logical_col_idx += 1
                continue

            use_unformatted = (
                unformatted_list[logical_col_idx]
                if unformatted_list and logical_col_idx < len(unformatted_list)
                else True
            )
            if use_unformatted:
                cell_text = self._clean_extracted_text(cell.get_text(separator="\n", strip=True))
            else:
                cell_text = self._clean_extracted_text(cell.decode_contents())

            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))

            # Add the value for the first logical column spanned by this cell
            cells.append(cell_text)
            colspans.append(colspan)
            rowspans.append(rowspan)

            # Set rowspan trackers for all physical columns spanned
            for i in range(colspan):
                while len(self._rowspan_trackers) <= physical_col_idx + i:
                    self._rowspan_trackers.append(None)
                if rowspan > 1:
                    value_for_tracker = cell_text if i == 0 else None
                    self._rowspan_trackers[physical_col_idx + i] = {
                        "value": value_for_tracker,
                        "rows_left": rowspan - 1,
                        "colspan": 1,
                    }
                else:
                    self._rowspan_trackers[physical_col_idx + i] = None

            physical_col_idx += colspan
            logical_col_idx += 1  # Only advance by 1 logical column per <td>
        return physical_col_idx

    def _check_circular_reference(self, row, visited_tables, table_nesting_level):
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
        self, included_table_tree: Node, level_nodes: Dict[int, Node], row_nesting_level: int, root: Node
    ) -> None:
        parent_node = level_nodes.get(row_nesting_level - 1, root)
        for child in included_table_tree.children:
            child.parent = parent_node

    def _create_node(
        self, node_name: str, row_data: Dict[str, Any], row_nesting_level: int, level_nodes: Dict[int, Node], root: Node
    ) -> None:
        parent_node = level_nodes.get(row_nesting_level - 1, root)
        self.logger.debug(
            f"Nesting Level: {row_nesting_level}, Name: {node_name}, "
            f"Parent: {parent_node.name if parent_node else 'None'}"
        )
        node = Node(node_name, parent=parent_node, **row_data)
        level_nodes[row_nesting_level] = node

    def _extract_header(self, table: Tag, column_to_attr: Dict[int, str]) -> list:
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
        - Replace space characters with underscores
        - Replace parentheses characters with dashes

        Args:
            input_string (str): The string to be sanitized.

        Returns:
            str: The sanitized string.

        """
        # Normalize the string to NFC form and transliterate to ASCII
        normalized_str = unidecode(input_string.lower())
        return re.sub(
            r"[ \-()']",
            lambda match: "-" if match.group(0) in "()" else "_",
            normalized_str,
        )
