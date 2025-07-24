"""DOM specification parser class for DICOM standard processing in dcmspec.

Provides the DOMSpecParser class for parsing DICOM specification tables from XHTML documents,
converting them into structured in-memory representations using anytree.
"""
import re
from unidecode import unidecode
from anytree import Node
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, Optional
from dcmspec.spec_parser import SpecParser
from dcmspec.dom_utils import DOMUtils

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
        skip_columns: Optional[list[int]] = None,
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
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a column.

        Returns:
            Tuple[Node, Node]: The metadata node and the table content node.

        """
        self._skipped_columns_flag = False

        content = self.parse_table(
            dom, table_id, column_to_attr, name_attr, include_depth=include_depth, skip_columns=skip_columns
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

    def parse_table(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int = 0,
        include_depth: Optional[int] = None,  # None means unlimited
        skip_columns: Optional[list[int]] = None,
        visited_tables: Optional[set] = None,
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
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a column.
            visited_tables (Optional[set]): Set of table IDs that have been visited to prevent infinite recursion.

        Returns:
            root: The root node of the tree representation of the specification table.

        """
        self.logger.info(f"Nesting Level: {table_nesting_level}, Parsing table with id {table_id}")
        
        # Initialize visited_tables set if not provided (first call)
        if visited_tables is None:
            visited_tables = set()
        
        # Add current table to visited set
        visited_tables.add(table_id)
        
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

        for row in table.find_all("tr")[1:]:
            row_data = self._extract_row_data(row, skip_columns=skip_columns)
            if row_data[name_attr] is None:
                continue  # Skip empty rows
            row_nesting_level = table_nesting_level + row_data[name_attr].count(">")

            # Add nesting level symbols to included table element names except if row is a title
            if table_nesting_level > 0 and not row_data[name_attr].isupper():
                row_data[name_attr] = ">" * table_nesting_level + row_data[name_attr]

            # Process Include statement unless include_depth is defined and not reached
            if "Include" in row_data[name_attr] and (include_depth is None or include_depth > 0):
                next_depth = None if include_depth is None else include_depth - 1
                
                # Check for circular reference before attempting to parse included table
                include_anchor = row.find("a", {"class": "xref"})
                should_include = True
                if include_anchor:
                    include_table_id = include_anchor["href"].split("#", 1)[-1]
                    if include_table_id in visited_tables:
                        self.logger.warning(
                            f"Nesting Level: {table_nesting_level}, Circular reference detected for "
                            f"table {include_table_id}, creating node instead of recursing"
                        )
                        should_include = False
                
                if should_include:
                    self._parse_included_table(
                        dom, row, column_to_attr, name_attr, row_nesting_level, next_depth, 
                        level_nodes, root, visited_tables
                    )
                else:
                    # Create a node to represent the circular reference instead of recursing
                    node_name = self._sanitize_string(row_data[name_attr])
                    self._create_node(node_name, row_data, row_nesting_level, level_nodes, root)
            else:
                node_name = self._sanitize_string(row_data[name_attr])
                self._create_node(node_name, row_data, row_nesting_level, level_nodes, root)

        self.logger.info(f"Nesting Level: {table_nesting_level}, Table parsed successfully")
        
        # Remove current table from visited set when exiting this level
        visited_tables.discard(table_id)
        
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

    def _extract_row_data(
            self, row: Tag, skip_columns: Optional[list[int]] = None) -> Dict[str, Any]:
        """Extract data from a table row.

        Processes each cell in the row, handling colspans and extracting text
        content from paragraphs within the cells. Constructs a dictionary
        containing the extracted data.

        If the row has one less cell than the mapping and skip_columns is set,
        those columns will be skipped for this row, allowing for robust alignment when
        a column is sometimes missing.

        Args:
            row: The table row element (BeautifulSoup Tag).
            table_nesting_level: The nesting level of the table.
            skip_columns (Optional[list[int]]): List of column indices to skip if the row is missing a column.

        Returns:
            A dictionary containing the extracted data from the row.

        """
        # Initialize rowspan trackers if not present
        if not hasattr(self, "_rowspan_trackers") or self._rowspan_trackers is None:
            self._rowspan_trackers = []

        # Add cells from pending rowspans
        cells, colspans, rowspans, col_idx = self._handle_pending_rowspans()

        # Process the actual cells in this row
        col_idx = self._process_actual_cells(row, cells, colspans, rowspans, col_idx)

        # Clean up rowspan trackers for cells that are no longer needed
        if len(self._rowspan_trackers) > col_idx:
            self._rowspan_trackers = self._rowspan_trackers[:col_idx]

        attr_indices = list(self.column_to_attr.keys())

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
        # sourcery skip: dict-comprehension, inline-immediately-returned-variable, inline-variable
        """Align cells to attributes when skip_columns is used.
        
        This method aligns the row's cells to the attribute indices, skipping the columns
        specified in skip_columns. It is used when the row is missing exactly the number of
        columns specified, ensuring the remaining cells are mapped to the correct attributes.

        """
        attr_indices = [i for i in attr_indices if i not in skip_columns]
        # Flag if the skipped_columns were actually skipped
        self._skipped_columns_flag = True
        row_data = {}
        for attr_index, (cell, colspan) in enumerate(zip(cells, colspans)):
            if attr_index < len(attr_indices):
                col_idx_map = attr_indices[attr_index]
                attr = self.column_to_attr[col_idx_map]
                row_data[attr] = cell
        return row_data

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
        cells = []
        colspans = []
        rowspans = []
        col_idx = 0
        for tracker in self._rowspan_trackers:
            if tracker and tracker["rows_left"] > 0:
                cells.append(tracker["value"])
                colspans.append(tracker["colspan"])
                rowspans.append(tracker["rows_left"])
                tracker["rows_left"] -= 1
                col_idx += tracker["colspan"]
        return cells, colspans, rowspans, col_idx

    def _process_actual_cells(self, row, cells, colspans, rowspans, col_idx):
        cell_iter = iter(row.find_all("td"))
        while True:
            if col_idx >= len(self._rowspan_trackers):
                self._rowspan_trackers.append(None)
            if self._rowspan_trackers[col_idx] and self._rowspan_trackers[col_idx]["rows_left"] > 0:
                # Already filled by rowspan above
                col_idx += self._rowspan_trackers[col_idx]["colspan"]
                continue
            try:
                cell = next(cell_iter)
            except StopIteration:
                break
            paragraphs = cell.find_all("p")
            if paragraphs:
                cell_text = "\n".join(p.text.strip() for p in paragraphs)
            else:
                # Handle cases where no <p> tags present
                cell_text = cell.get_text(strip=True)
            
            # Clean the extracted text to remove encoding artifacts
            cell_text = self._clean_extracted_text(cell_text)
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            cells.append(cell_text)
            colspans.append(colspan)
            rowspans.append(rowspan)

            for i in range(colspan):
                while len(self._rowspan_trackers) <= col_idx + i:
                    self._rowspan_trackers.append(None)
                # If rowspan > 1, track for future rows
                if rowspan > 1:
                    self._rowspan_trackers[col_idx + i] = {
                        "value": cell_text,
                        "rows_left": rowspan - 1,
                        "colspan": 1,
                    }
                else:
                    self._rowspan_trackers[col_idx + i] = None
            col_idx += colspan
        return col_idx

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
        """Clean extracted text by removing common encoding artifacts and Unicode issues.

        Args:
            text (str): The text to be cleaned.

        Returns:
            str: The cleaned text.

        """
        # Remove common encoding artifacts
        cleaned = text.replace('\u00c2', '')  # Remove Â character
        cleaned = cleaned.replace('\u00a0', ' ')  # Replace non-breaking space with regular space
        cleaned = cleaned.replace('\u200b', '')  # Remove zero-width space
        
        # Clean up Unicode quote characters that cause issues
        cleaned = cleaned.replace('\u00e2\u0080\u009c', '"')  # Replace left double quotation mark
        cleaned = cleaned.replace('\u00e2\u0080\u009d', '"')  # Replace right double quotation mark
        cleaned = cleaned.replace('\u2018', "'")  # Replace left single quotation mark
        cleaned = cleaned.replace('\u2019', "'")  # Replace right single quotation mark
        cleaned = cleaned.replace('\u201c', '"')  # Replace left double quotation mark
        cleaned = cleaned.replace('\u201d', '"')  # Replace right double quotation mark
        
        # Handle em dash and en dash
        cleaned = cleaned.replace('\u2014', '-')  # Replace em dash
        cleaned = cleaned.replace('\u2013', '-')  # Replace en dash
        
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
