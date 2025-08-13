"""XHTML document handler class for DICOM standard processing in dcmspec.

Provides the XHTMLDocHandler class for downloading, caching, and parsing XHTML documents
from the DICOM standard, returning a BeautifulSoup DOM object.
"""

from collections.abc import Callable
import logging
import os
import re
from bs4 import BeautifulSoup
from typing import Optional

from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler


class XHTMLDocHandler(DocHandler):
    """Handler class for DICOM specifications documents in XHTML format.

    Provides methods to download, cache, and parse XHTML documents, returning a BeautifulSoup DOM object.
    Inherits configuration and logging from DocHandler.
    """

    def __init__(self, config: Optional[Config] = None, logger: Optional[logging.Logger] = None):
        """Initialize the XHTML document handler and set cache_file_name to None."""
        super().__init__(config=config, logger=logger)
        self.cache_file_name = None

    def load_document(
            self, cache_file_name: str,
            url: Optional[str] = None,
            force_download: bool = False,
            progress_callback: 'Optional[Callable[[int], None]]' = None
    ) -> BeautifulSoup:
        """Open and parse an XHTML file, downloading it if needed.

        Args:
            cache_file_name (str): Path to the local cached XHTML file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool): If True, do not use cache and download the file from the URL.
            progress_callback (Optional[Callable[[int], None]]): Optional callback to report download progress.
                The callback receives an integer percent (0-100). If the total file size is unknown,
                the callback will be called with -1 to indicate indeterminate progress.

        Returns:
            BeautifulSoup: Parsed DOM.

        """
        # Set cache_file_name as an attribute for downstream use (e.g., in SpecFactory)
        self.cache_file_name = cache_file_name

        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        need_download = force_download or (not os.path.exists(cache_file_path))
        if need_download:
            if not url:
                raise ValueError("URL must be provided to download the file.")
            cache_file_path = self.download(url, cache_file_name, progress_callback=progress_callback)
        return self.parse_dom(cache_file_path)

    def download(
        self,
        url: str,
        cache_file_name: str,
        progress_callback: 'Optional[Callable[[int], None]]' = None
    ) -> str:
        """Download and cache an XHTML file from a URL.

        Uses the base class download method, saving as UTF-8 text and cleaning ZWSP/NBSP.

        Args:
            url: The URL of the XHTML document to download.
            cache_file_name: The filename of the cached document.
            progress_callback: Optional callback to report download progress.

        Returns:
            The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        return super().download(url, file_path, binary=False, progress_callback=progress_callback)

    def clean_text(self, text: str) -> str:
        """Clean text content before saving.

        Removes zero-width space (ZWSP) and non-breaking space (NBSP) characters.

        Args:
            text (str): The text content to clean.

        Returns:
            str: The cleaned text.

        """
        cleaned_content = re.sub(r"\u200b", "", text)
        cleaned_content = re.sub(r"\u00a0", " ", cleaned_content)
        return cleaned_content

    def parse_dom(self, file_path: str) -> BeautifulSoup:
        """Parse a cached XHTML file into a BeautifulSoup DOM object.

        Args:
            file_path (str): Path to the cached XHTML file to parse.

        Returns:
            BeautifulSoup: The parsed DOM object.

        Raises:
            RuntimeError: If the file cannot be read or parsed.

        """
        self.logger.info(f"Reading XHTML DOM from {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # dom = BeautifulSoup(content, "html.parser")  # use python HTML parser. Fine for XHTML. Unreliable for XML.
            # dom = BeautifulSoup(content, "lxml")  # use lxml package parser. Default to HTML and generates a warning.
            dom = BeautifulSoup(content, features="xml")  # use lxml package parser. Force using XML. Safest choice.
            self.logger.info("XHTML DOM read successfully")

            return dom
        except OSError as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise RuntimeError(f"Failed to read file {file_path}: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to parse XHTML file {file_path}: {e}")
            raise RuntimeError(f"Failed to parse XHTML file {file_path}: {e}") from e

    def _patch_table(self, dom: BeautifulSoup, table_id: str) -> None:
        """Patch an XHTML table to fix potential errors.

        This method does nothing and may be overridden in derived classes if patching is needed.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            table_id (str): The ID of the table to patch.

        Returns:
            None
            
        """
        pass
