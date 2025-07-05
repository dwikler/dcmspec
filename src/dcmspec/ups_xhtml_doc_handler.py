"""UPSXHTMLDocHandler for DICOM UPS table patching in dcmspec.

Provides the UPSXHTMLDocHandler class, a subclass of XHTMLDocHandler, which applies
UPS-specific patching to DICOM XHTML tables after parsing.
"""

from bs4 import BeautifulSoup
from dcmspec.dom_utils import DOMUtils
from dcmspec.xhtml_doc_handler import XHTMLDocHandler

class UPSXHTMLDocHandler(XHTMLDocHandler):
    """Subclass of XHTMLDocHandler that applies UPS-specific table patching.

    This handler applies UPS-specific patching to DICOM XHTML tables after parsing.
    It corrects known issues in Table CC.2.5-3 of DICOM PS3.4, where 'Include' rows under certain
    sequence attribute rows are missing a '>' nesting symbol. The affected sequences are:
        - Output Information Sequence
        - Gender Identity Code Sequence
        - Sex Parameters for Clinical Use Category Code Sequence
        - Pronoun Code Sequence
    """

    def __init__(self, config=None, logger=None):
        """Initialize the UPSXHTMLDocHandler.

        Sets up the handler with the given configuration and logger, and creates a DOMUtils
        instance for DOM navigation.

        Args:
            config (optional): Configuration object for the handler.
            logger (optional): Logger instance to use. If None, a default logger is created.

        """
        super().__init__(config=config, logger=logger)
        self.dom_utils = DOMUtils(logger=self.logger)
        
    def parse_dom(self, file_path: str) -> BeautifulSoup:
        """Parse a cached XHTML file and apply UPS-specific table patching.

        Calls the base class's parse_dom, then patches the Output Information Sequence Include nesting level.

        Args:
            file_path (str): Path to the cached XHTML file to parse.

        Returns:
            BeautifulSoup: The patched DOM object.

        """
        dom = super().parse_dom(file_path)
        # Patch the table after parsing
        self._patch_table(dom, "table_CC.2.5-3")  # or pass table_id dynamically if needed
        return dom

    def _patch_table(self, dom, table_id):
        """Patch the specified XHTML table to fix Include nesting level errors.

        In the UPS, the 'Include' row under some sequence attribute rows are missing one '>' nesting symbol.

        Args:
            dom: The BeautifulSoup DOM object representing the XHTML document.
            table_id: The ID of the table to patch.

        """
        patch_labels = [
            ">Output Information Sequence",
            ">Gender Identity Code Sequence",
            ">Sex Parameters for Clinical Use Category Code Sequence",
            ">Pronoun Code Sequence",
        ]
        for label in patch_labels:
            target_element_id = self._search_element_id(dom, table_id, label)
            if not target_element_id:
                self.logger.warning(f"{label} Include Row element ID not found")
                continue
            element = dom.find(id=target_element_id).find_parent()
            span_element = element.find("span", class_="italic")
            if span_element:
                children_to_modify = [
                    child for child in span_element.children
                    if isinstance(child, str) and ">Include" in child
                ]
                for child in children_to_modify:
                    new_text = child.replace(">Include", ">>Include")
                    child.replace_with(new_text)

    def _search_element_id(self, dom, table_id, sequence_label):
        table = self.dom_utils.get_table(dom, table_id)
        if not table:
            return None

        self.logger.debug(f"Table with id {table_id} found")
        tr_elements = table.find_all("tr")
        include_id = self._search_sequence_include_id(tr_elements, sequence_label)

        if include_id is None:
            self.logger.debug("No <tr> matching criteria found")

        return include_id

    def _search_sequence_include_id(self, tr_elements, sequence_label):
        target_found = False
        for tr in tr_elements:
            first_td = tr.find("td")
            if first_td and first_td.get_text(strip=True) == sequence_label:
                self.logger.debug(f"{sequence_label} row found")
                target_found = True
                break

        if target_found:
            tr = tr.find_next("tr")
            if tr is not None:
                first_td = tr.find("td")
                if first_td and first_td.get_text(strip=True).startswith(">Include"):
                    self.logger.debug("Include <tr> found")
                    return first_td.find("a")["id"]

        return None
