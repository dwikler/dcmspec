"""DOM utility functions for DICOM XHTML document processing in dcmspec.

Provides the DOMUtils class, which offers methods for navigating and extracting
tables and table IDs from parsed BeautifulSoup DOMs of DICOM standard documents.

Typical usage:
    dom_utils = DOMUtils(logger=logger)
    table = dom_utils.get_table(dom, table_id)
    table_id = dom_utils.get_table_id_from_section(dom, section_id)
"""
import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag

class DOMUtils:
    """Utility class for DOM navigation and extraction in DICOM XHTML documents.

    Provides methods for locating tables and table IDs within a parsed BeautifulSoup DOM,
    with optional logging for warnings and debug information.

    Typical usage:
        ```python
        dom_utils = DOMUtils(logger=logger)
        table = dom_utils.get_table(dom, table_id)
        table_id = dom_utils.get_table_id_from_section(dom, section_id)
        ```

    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize DOMUtils with an optional logger.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use for warnings and debug messages.
                If None, a default logger is created.

        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def get_table(self, dom: BeautifulSoup, table_id: str) -> Optional[Tag]:
        """Retrieve the table element with the specified ID from the DOM.

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
        table_div = anchor.find_parent("div", class_="table")
        if not table_div:
            self.logger.warning(f"Parent <div class='table'> for Table Id {table_id} not found.")
            return None
        table = table_div.find("table")
        if not table:
            self.logger.warning(f"Table for Table Id {table_id} not found inside its <div class='table'>.")
            return None
        return table
    
    def get_table_id_from_section(self, dom: BeautifulSoup, section_id: str) -> Optional[str]:
        """Get the id of the first table in a section.

        Retrieve the first table_id (anchor id) of a `<div class="table">` inside a `<div class="section">`
        that contains an anchor tag with the given section id, e.g.:

        ```html
        <a id="table_C.7-1" shape="rect"></a>
        ```

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            section_id (str): The id of the section to search for the table_id.

        Returns:
            Optional[str]: The id of the first table anchor found, or None if not found.

        """
        # Find the anchor with the given id
        anchor = dom.find("a", {"id": section_id})
        if not anchor:
            self.logger.warning(f"Section with id '{section_id}' not found.")
            return None

        # Find the parent section div
        section_div = anchor.find_parent("div", class_="section")
        if not section_div:
            self.logger.warning(f"No parent <div class='section'> found for section id '{section_id}'.")
            return None

        # Find the first <div class="table"> inside the section
        table_div = section_div.find("div", class_="table")
        if not table_div:
            self.logger.warning(f"No <div class='table'> found in section for section id '{section_id}'.")
            return None

        # Find the first anchor with an id inside the table div (the table id)
        table_anchor = table_div.find("a", id=True)
        if table_anchor and table_anchor.get("id"):
            return table_anchor["id"]

        self.logger.warning(f"No table id found in <div class='table'> for section id '{section_id}'.")
        return None
