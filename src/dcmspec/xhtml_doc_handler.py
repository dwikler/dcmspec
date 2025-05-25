import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
from dcmspec.doc_handler import DocHandler


class XHTMLDocHandler(DocHandler):

    def get_dom(self, cache_file_name: str, url: Optional[str] = None, force_download: bool = False) -> BeautifulSoup:
        """
        Opens and parses an XHTML file, downloading it if needed.

        Args:
            file_path (str): Path to the local XHTML file.
            url (str, optional): URL to download the file from if not present or force_download is True.
            force_download (bool): If True, always download the file from the URL.

        Returns:
            BeautifulSoup: Parsed DOM.
        """
        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        if force_download or (not os.path.exists(cache_file_path)):
            if not url:
                raise ValueError("URL must be provided to download the file.")
            cache_file_path = self.download(url, cache_file_name)
        return self.parse_dom(cache_file_path)

    def download(self, url: str, cache_file_name: str) -> str:
        """
        Downloads an XHTML file from a URL and saves it to file_path.
        Raises a RuntimeError if the download or save fails.

        The URL from a Part of the DICOM standard in HTML or a Part section
        in CHTML format containing Attributes tables is expected.

        Retrieves the XHTML content and saves it to the given file path,
        creating any necessary directories.

        Args:
            url: The URL of the XHTML document to download.
            cache_file_name: The filename of the cached document.

        Returns:
            The file path where the document was saved.
        """
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        self.logger.info(f"Downloading XHTML document from {url} to {file_path}")
        try:
            # Create the destination folder if it does not exist
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Force UTF-8 decoding to avoid getting Ã (/u00C3) characters
            response.encoding = "utf-8"
            # html_content = response.content.decode("utf-8", errors="ignore")
            html_content = response.text
            with open(file_path, "w", encoding="utf-8") as f:
                # Replace ZWSP with nothing and NBSP with a regular space
                cleaned_content = re.sub(r"\u200b", "", html_content)
                cleaned_content = re.sub(r"\u00a0", " ", cleaned_content)

                f.write(cleaned_content)
            self.logger.info(f"Document downloaded to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            raise RuntimeError(f"Failed to download {url}: {e}")
        except OSError as e:
            self.logger.error(f"Failed to save file {file_path}: {e}")
            raise RuntimeError(f"Failed to save file {file_path}: {e}")

    def parse_dom(self, file_path: str) -> BeautifulSoup:
        """
        Parses a local XHTML file and returns a BeautifulSoup DOM.
        Raises a RuntimeError if the file cannot be read or parsed.
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
            raise RuntimeError(f"Failed to read file {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to parse XHTML file {file_path}: {e}")
            raise RuntimeError(f"Failed to parse XHTML file {file_path}: {e}")

    def _patch_table(self, dom, table_id):
        """
        Patches the XHTML table to fix potential errors.

        This method does nothing and may be overridden in derived classes if patching is needed.
        """
        pass
