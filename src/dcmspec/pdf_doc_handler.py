"""PDF document handler for IHE Technical Frameworks or Supplements processing in dcmspec.

Provides the PDFDocHandler class for downloading, caching, and parsing PDF documents
from IHE Technical Frameworks or Supplements, returning CSV data from tables in PDF files.
"""

import os
import logging
from typing import Optional, List

import pdfplumber

from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler

class PDFDocHandler(DocHandler):
    """Handler class for extracting tables from PDF documents.

    Provides methods to download, cache, and extract tables as CSV data from PDF files.
    """

    def __init__(self, config: Optional[Config] = None, logger: Optional[logging.Logger] = None):
        """Initialize the PDF document handler.

        Sets up the handler with an optional configuration and logger.

        Args:
            config (Optional[Config]): Configuration object for cache and other settings.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        super().__init__(config=config, logger=logger)
        self.logger.debug(f"PDFDocHandler initialized with logger {self.logger.name} "
                          f"at level {logging.getLevelName(self.logger.level)}")

        self.cache_file_name = None

    def load_document(
        self,
        cache_file_name: str,
        url: Optional[str] = None,
        force_download: bool = False,
        page_numbers: Optional[list] = None,
        table_indices: Optional[list] = None,
        table_id: Optional[str] = None,
    ) -> dict:
        """Download, cache, and extract the logical CSV table from the PDF.

        Args:
            cache_file_name (str): Path to the local cached PDF file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool): If True, do not use cache and download the file from the URL.
            page_numbers (list, optional): List of page numbers to extract tables from.
            table_indices (list, optional): List of (page, index) tuples specifying which tables to concatenate.
            table_id (str, optional): An identifier for the concatenated table.

        Returns:
            dict: The specification table dict with keys 'header', 'data', and optionally 'table_id'.

        """
        self.cache_file_name = cache_file_name
        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        need_download = force_download or (not os.path.exists(cache_file_path))
        if need_download:
            if not url:
                self.logger.error("URL must be provided to download the file.")
                raise ValueError("URL must be provided to download the file.")
            self.logger.info(f"Downloading PDF from {url} to {cache_file_path}")
            cache_file_path = self.download(url, cache_file_name)
        else:
            self.logger.info(f"Loading PDF from cache file {cache_file_path}")
        import pdfplumber
        pdf = pdfplumber.open(cache_file_path)

        if page_numbers is None or table_indices is None:
            self.logger.error("page_numbers and table_indices must be provided to extract the logical table.")
            raise ValueError("page_numbers and table_indices must be provided to extract the logical table.")

        self.logger.debug(f"Extracting tables from pages: {page_numbers}")
        all_tables = self.extract_tables(pdf, page_numbers)
        self.logger.debug(f"Extracted {len(all_tables)} tables from PDF.")
        self.logger.debug(f"Concatenating tables with indices: {table_indices}")
        spec_table = self.concat_tables(all_tables, table_indices, table_id=table_id)
        self.logger.debug(f"Returning spec_table with header: {spec_table.get('header', [])}")
        pdf.close()
        return spec_table


    def download(self, url: str, cache_file_name: str) -> str:
        """Download and cache a PDF file from a URL using the base class download method.

        Args:
            url: The URL of the PDF document to download.
            cache_file_name: The filename of the cached document.

        Returns:
            The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        return super().download(url, file_path, binary=True)

    def extract_tables(
        self,
        pdf: pdfplumber.PDF,
        page_numbers: List[int],
    ) -> List[dict]:
        """Extract and return all tables from the specified PDF pages.

        Args:
            pdf (pdfplumber.PDF): The PDF object.
            page_numbers (List[int]): List of page numbers (1-indexed) to extract tables from.

        Returns:
            List[dict]: List of dicts, each with keys 'page', 'index', 'data' (table as list of rows),
            and 'header' (list of header cells).

        Raises:
            IndexError: If a page number is out of range for the PDF.

        """
        all_tables = []
        num_pages = len(pdf.pages)
        for page_num in page_numbers:
            if not (1 <= page_num <= num_pages):
                raise IndexError(
                    f"Page number {page_num} is out of range for this PDF (valid range: 1 to {num_pages})"
                )
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables()
            if tables:
                for idx, table in enumerate(tables):
                    # Remove empty columns and clean up each row
                    cleaned_table = [
                        [cell for cell in row if cell not in ("", None)]
                        for row in table
                    ]
                    header = cleaned_table[0] if cleaned_table else []
                    data = cleaned_table[1:] if len(cleaned_table) > 1 else []
                    all_tables.append({
                        "page": page_num,
                        "index": idx,
                        "header": header,
                        "data": data,
                    })
        return all_tables

    def concat_tables(
        self,
        tables: List[dict],
        table_indices: List[tuple],
        table_id: str = None,
    ) -> dict:
        """Concatenate selected tables (across pages or by specification) into a single logical table.

        Args:
            tables (List[dict]): List of table dicts, each with 'page', 'index', 'header', and 'data'.
            table_indices (List[tuple]): List of (page, index) tuples specifying which tables to concatenate,
                in the order they should be concatenated.
            table_id (str, optional): An identifier for the concatenated table.

        Returns:
            dict: A dict with keys 'table_id' (if provided), 'header' (from the first table), 
            and 'data' (the concatenated table as a list of rows).

        Example:
            ```python
            table_indices = [(57, 1), (58, 0), (60, 0)]
            concatenated = handler.concat_tables(
                all_tables,
                table_indices,
                table_id="tdwii_ups_scheduled_info_base"
            )
            ```

        """
        grouped_table = []
        header = []
        first = True
        for page, idx in table_indices:
            for table in tables:
                if table["page"] == page and table["index"] == idx:
                    if first:
                        header = table.get("header", [])
                        first = False
                    elif header and table.get("header", []) != header:
                        self.logger.warning(
                            f"Header mismatch in concatenated tables: {header} != {table.get('header', [])} "
                            f"(page {page}, index {idx})"
                        )
                    n_columns = len(header)
                    for row in table["data"]:
                        # Always pad/truncate to header length
                        row = (row + [""] * (n_columns - len(row)))[:n_columns]
                        grouped_table.append(row)
        result = {"header": header, "data": grouped_table}
        if table_id is not None:
            result["table_id"] = table_id
        return result

    def extract_notes(
        self,
        pdf: pdfplumber.PDF,
        page_numbers: List[int],
        table_id: str = None,
        note_pattern: str = r"^\d*\s*Note\s\d+:",
        header_footer_pattern: str = r"^\s*(IHE|_{3,}|Rev\.|Copyright|Template|Page\s\d+|\(TDW-II\))",
        line_number_pattern: str = r"^\d+\s",
        end_note_pattern: str = r".*7\.5\.1\.1\.2",
    ) -> dict:
        """Extract notes referenced in tables from the specified PDF pages.

        Args:
            pdf (pdfplumber.PDF): The PDF object.
            page_numbers (List[int]): List of page numbers (1-indexed) to extract notes from.
            table_id (str, optional): The table_id to associate with these notes.
            note_pattern (str): Regex pattern to identify note lines.
            header_footer_pattern (str): Regex pattern to skip header/footer lines.
            line_number_pattern (str): Regex pattern to remove line numbers.
            end_note_pattern (str): Regex pattern to identify the end of notes section.

        Returns:
            dict: Mapping from note key (e.g., "Note 1:") to a dict with 'text' and 'table_id' (if provided).

        Example return:
            {
                "Note 1:": {"text": "...", "table_id": "T-7.5-1"},
                "Note 2:": {"text": "...", "table_id": "T-7.5-1"},
            }

        """
        import re

        notes = {}
        note_re = re.compile(note_pattern)
        header_footer_re = re.compile(header_footer_pattern)
        line_number_re = re.compile(line_number_pattern)
        end_note_re = re.compile(end_note_pattern)
        current_note = None

        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                for line in lines:
                    # Always skip header/footer lines, even in note continuation
                    if header_footer_re.search(line):
                        continue
                    if end_note_re.search(line):
                        current_note = None
                        break
                    match = note_re.search(line)
                    if match:
                        note_number = match.group().strip()
                        note_number = re.sub(r"^\d*\s*", "", note_number)
                        note_text = line[match.end():].strip()
                        notes[note_number] = {
                            "text": note_text,
                            "table_id": table_id
                        } if table_id else {"text": note_text}
                        current_note = note_number
                    elif current_note:
                        line = line_number_re.sub("", line).strip()
                        notes[current_note]["text"] += f" {line}"
        if notes:
            self.logger.debug(f"Extracted notes: {list(notes.keys())}")
        return notes