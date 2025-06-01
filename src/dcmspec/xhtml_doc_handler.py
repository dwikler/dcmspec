"""XHTML document handler class for DICOM standard processing in dcmspec.

Provides the XHTMLDocHandler class for downloading, caching, and parsing XHTML documents
from the DICOM standard, returning a BeautifulSoup DOM object.
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
from dcmspec.doc_handler import DocHandler


class XHTMLDocHandler(DocHandler):
    """Handler class for DICOM specifications documents in XHTML format.

    Provides methods to download, cache, and parse XHTML documents, returning a BeautifulSoup DOM object.
    Inherits configuration and logging from DocHandler.
    """

    def get_dom(self, cache_file_name: str, url: Optional[str] = None, force_download: bool = False) -> BeautifulSoup:
        """Open and parse an XHTML file, downloading it if needed.

        Args:
            cache_file_name (str): Path to the local cached XHTML file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool): If True, do not use cache and download the file from the URL.

        Returns:
            BeautifulSoup: Parsed DOM.

        """
        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        need_download = force_download or (not os.path.exists(cache_file_path))
        if need_download:
            if not url:
                raise ValueError("URL must be provided to download the file.")
            cache_file_path = self.download(url, cache_file_name)
        return self.parse_dom(cache_file_path)

    def download(self, url: str, cache_file_name: str) -> str:
        """Download and cache an XHTML file from a URL.

        Args:
            url: The URL of the XHTML document to download.
            cache_file_name: The filename of the cached document.

        Returns:
            The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        self.logger.info(f"Downloading XHTML document from {url} to {file_path}")
        try:
            self._ensure_dir_exists(file_path)  # Fail before download if directory can't be created
        except OSError as e:
            self.logger.error(f"Failed to create directory for {file_path}: {e}")
            raise RuntimeError(f"Failed to create directory for {file_path}: {e}") from e
        try:
            html_content = self._fetch_url_content(url)
            self._save_content(file_path, html_content)
            self.logger.info(f"Document downloaded to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            raise RuntimeError(f"Failed to download {url}: {e}") from e
        except OSError as e:
            self.logger.error(f"Failed to save file {file_path}: {e}")
            raise RuntimeError(f"Failed to save file {file_path}: {e}") from e

    def _ensure_dir_exists(self, file_path: str) -> None:
        """Ensure the directory for the file path exists."""
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _fetch_url_content(self, url: str) -> str:
        """Fetch content from a URL and return as UTF-8 text."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Force UTF-8 decoding to avoid getting Ã (/u00C3) characters
        response.encoding = "utf-8"
        # IN the future we may want to manually decode the content and ignore errors:
        # html_content = response.content.decode("utf-8", errors="ignore")
        # return html_content
        return response.text

    def _save_content(self, file_path: str, html_content: str) -> None:
        """Clean and save HTML content to a file."""
        with open(file_path, "w", encoding="utf-8") as f:
            # Replace ZWSP with nothing and NBSP with a regular space
            cleaned_content = re.sub(r"\u200b", "", html_content)
            cleaned_content = re.sub(r"\u00a0", " ", cleaned_content)
            f.write(cleaned_content)

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
