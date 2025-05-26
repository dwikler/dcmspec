import re
from unidecode import unidecode
from anytree import Node
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, Optional
from dcmspec.spec_parser import SpecParser


class DOMSpecParser(SpecParser):
    def parse(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int = 0,
        include_depth: Optional[int] = None,  # None means unlimited
    ):
        """
        Parses specification metadata and content from tables within the DOM of a DICOM document
        and converts the document format into a structured representation.
        """
        metadata = self.parse_metadata(dom, table_id, column_to_attr)
        attr_tree = self.parse_table(dom, table_id, column_to_attr, name_attr, include_depth=include_depth)
        return metadata, attr_tree

    def parse_table(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
        name_attr: str,
        table_nesting_level: int = 0,
        include_depth: Optional[int] = None,  # None means unlimited
    ) -> Node:
        """
        Parses specification content from tables within the DOM of a DICOM document.

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

        Returns:
            root: The root node of the tree representation of the specification table.
        """
        self.logger.info(f"Nesting Level: {table_nesting_level}, Parsing table with id {table_id}")
        # Maps column indices in the DICOM standard table to corresponding node attribute names
        # for constructing a tree-like representation of the table's data.
        # self.column_to_attr = {**{0: "elem_name", 1: "elem_tag"}, **(column_to_attr or {})}

        table = self.get_table(dom, table_id)
        if not table:
            raise ValueError(f"Table with id '{table_id}' not found.")

        if not column_to_attr:
            raise ValueError("Columns to node attributes missing.")
        else:
            self.column_to_attr = column_to_attr

        root = Node("content")
        level_nodes: Dict[int, Node] = {0: root}

        for row in table.find_all("tr")[1:]:
            row_data = self._extract_row_data(row, table_nesting_level)

            row_nesting_level = table_nesting_level + row_data[name_attr].count(">")

            # Add nesting level symbols to included table element names except if row is a title
            if table_nesting_level > 0 and not row_data[name_attr].isupper():
                row_data[name_attr] = ">" * table_nesting_level + row_data[name_attr]

            # Process Include statement unless include_depth is defined and not reached
            if "Include" in row_data[name_attr] and (include_depth is None or include_depth > 0):
                next_depth = None if include_depth is None else include_depth - 1
                self._parse_included_table(
                    dom, row, column_to_attr, name_attr, row_nesting_level, next_depth, level_nodes, root
                )
            else:
                node_name = self._sanitize_string(row_data[name_attr])
                self._create_node(node_name, row_data, row_nesting_level, level_nodes, root)

        self.logger.info(f"Nesting Level: {table_nesting_level}, Table parsed successfully")
        return root

    def parse_metadata(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Dict[int, str],
    ) -> Node:
        """
        Parses specification metadata from the document and the table within the DOM of a DICOM document.

        This method extracts the version of the DICOM standard and the headers of the tables.

        Args:
            dom: The BeautifulSoup DOM object.
            table_id: The ID of the table to parse.
            column_to_attr: Mapping between index of columns to parse and attributes name

        Returns:
            metadata_node: The root node of the tree representation of the specification metadata.
        """
        table = self.get_table(dom, table_id)
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
        """Retrieves the DICOM Standard version from the DOM.

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
        """Extracts version of DICOM books in HTML format"""
        titlepage = dom.find("div", class_="titlepage")
        if titlepage:
            subtitle = titlepage.find("h2", class_="subtitle")
        if subtitle:
            return subtitle.text.split()[2]
        return None

    def _version_from_section(self, dom):
        """Extracts version of DICOM sections in the CHTML format"""
        document_release = dom.find("span", class_="documentreleaseinformation")
        if document_release:
            return document_release.text.split()[2]
        return None

    def get_table(self, dom: BeautifulSoup, table_id: str) -> Optional[Tag]:
        """Retrieves the table element with the specified ID from the DOM.

        DocBook XML to XHTML conversion stylesheets enclose tables in a
        <div class="table"> with the table identifier in <a id="table_ID"></a>

        Searches for an anchor tag with the given ID and then finds the next
        table element.

        Args:
            dom: The BeautifulSoup DOM object.
            table_id: The ID of the table to retrieve.

        Returns:
            The table element if found, otherwise None.
        """
        anchor = dom.find("a", {"id": table_id})
        if anchor is None:
            self.logger.warning(f"Table Id {table_id} not found.")
            return None
        table = anchor.find_next("table")
        if not table:
            self.logger.warning(f"Table {table_id} not found.")
            return None
        return table

    def _extract_row_data(self, row: Tag, table_nesting_level: int) -> Dict[str, Any]:
        """Extracts data from a table row.

        Processes each cell in the row, handling colspans and extracting text
        content from paragraphs within the cells. Constructs a dictionary
        containing the extracted data.

        Args:
            row: The table row element (BeautifulSoup Tag).
            table_nesting_level: The nesting level of the table.

        Returns:
            A dictionary containing the extracted data from the row.
        """
        # Initialize rowspan trackers if not present
        if not hasattr(self, "_rowspan_trackers") or self._rowspan_trackers is None:
            self._rowspan_trackers = []

        cells = []
        colspans = []
        rowspans = []

        # Insert any pending rowspan values from previous rows
        col_idx = 0
        pending_rowspan_cells = []
        for tracker in self._rowspan_trackers:
            if tracker and tracker["rows_left"] > 0:
                cells.append(tracker["value"])
                colspans.append(tracker["colspan"])
                rowspans.append(tracker["rows_left"])
                tracker["rows_left"] -= 1
                col_idx += tracker["colspan"]
            else:
                pending_rowspan_cells.append(None)

        # Now process the actual cells in this row
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
            cell_text = "\n".join(p.text.strip() for p in paragraphs) if paragraphs else ""
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            cells.append(cell_text)
            colspans.append(colspan)
            rowspans.append(rowspan)
            # If rowspan > 1, track for future rows
            if rowspan > 1:
                for i in range(colspan):
                    self._rowspan_trackers[col_idx + i] = {
                        "value": cell_text,
                        "rows_left": rowspan - 1,
                        "colspan": 1,
                    }
            else:
                for i in range(colspan):
                    self._rowspan_trackers[col_idx + i] = None
            col_idx += colspan

        # Clean up trackers for columns that are no longer needed
        if len(self._rowspan_trackers) > col_idx:
            self._rowspan_trackers = self._rowspan_trackers[:col_idx]

        row_data: Dict[str, Any] = {}
        attr_index = 0
        for cell, colspan in zip(cells, colspans):
            if attr_index in self.column_to_attr:
                row_data[self.column_to_attr[attr_index]] = cell
            attr_index += colspan

        return row_data

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
    ) -> None:
        """Recursively parse Included Table"""
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
        """Extracts headers from the table and saves them in the headers attribute.

        Only extracts headers of the columns corresponding to the keys in column_to_attr.

        Args:
            table: The table element from which to extract headers.
        """
        cells = table.find_all("th")
        header = [header.get_text(strip=True) for i, header in enumerate(cells) if i in column_to_attr]
        self.logger.info(f"Extracted Header: {header}")
        return header

    def _sanitize_string(self, input_string: str) -> str:
        """
        Sanitize string to use it as a node attribute name:
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
        # Replace specified characters with underscores or hyphens
        sanitized_str = re.sub(r"[ \-()']", lambda match: "-" if match.group(0) in "()" else "_", normalized_str)
        return sanitized_str
