"""XHTML document handler class for DICOM standard processing in dcmspec.

Provides the XHTMLDocHandler class for downloading, caching, and parsing XHTML documents
from the DICOM standard, returning a BeautifulSoup DOM object.
"""

import logging
import os
import re
from bs4 import BeautifulSoup
from typing import Optional
# BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
from dcmspec.progress import handle_legacy_callback
from typing import Callable
# END LEGACY SUPPORT

from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler
from dcmspec.progress import ProgressObserver, ProgressStatus, Progress


class XHTMLDocHandler(DocHandler):
    """Handler class for DICOM specifications documents in XHTML format.

    Provides methods to download, cache, and parse XHTML documents, returning a BeautifulSoup DOM object.
    Inherits configuration and logging from DocHandler.

    Note:
    Progress reporting via progress_observer covers both downloading and caching (writing to disk).
    Parsing and cache loading are typically fast and do not emit progress updates.

    """

    def __init__(self, config: Optional[Config] = None, logger: Optional[logging.Logger] = None):
        """Initialize the XHTML document handler and set cache_file_name to None."""
        super().__init__(config=config, logger=logger)
        self.cache_file_name = None

    def load_document(
            self, cache_file_name: str,
            url: Optional[str] = None,
            force_download: bool = False,
            progress_observer: 'Optional[ProgressObserver]' = None,
            # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
            progress_callback: 'Optional[Callable[[int], None]]' = None,
            # END LEGACY SUPPORT
    ) -> BeautifulSoup:
        # sourcery skip: merge-else-if-into-elif, reintroduce-else, swap-if-else-branches
        """Open and parse an XHTML file, downloading it if needed.

        Args:
            cache_file_name (str): Path to the local cached XHTML file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool): If True, do not use cache and download the file from the URL.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.

        Returns:
            BeautifulSoup: Parsed DOM.

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT

        # Set cache_file_name as an attribute for downstream use (e.g., in SpecFactory)
        self.cache_file_name = cache_file_name

        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        need_download = force_download or (not os.path.exists(cache_file_path))
        if need_download:
            if not url:
                raise ValueError("URL must be provided to download the file.")
            cache_file_path = self.download(url, cache_file_name, progress_observer=progress_observer)
        else:
            # Also report progress when XHTML file was loaded from cache (keeping DOWNLOADING status for consistency)
            if progress_observer:
                progress_observer(Progress(100, status=ProgressStatus.DOWNLOADING))     

        # No need to report progress for parsing as, even for the largest DICOM standard XHTML file of 35 MB,
        # the parsing is fast and not a bottleneck. If future files or operations make parsing slow,
        # consider extending progress reporting here.
        return self.parse_dom(cache_file_path)

    def download(
        self,
        url: str,
        cache_file_name: str,
        progress_observer: 'Optional[ProgressObserver]' = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: 'Optional[Callable[[int], None]]' = None
        # END LEGACY SUPPORT
    ) -> str:
        """Download and cache an XHTML file from a URL.

        Uses the base class download method, saving as UTF-8 text and cleaning ZWSP/NBSP.

        Args:
            url: The URL of the XHTML document to download.
            cache_file_name: The filename of the cached document.
            progress_observer: Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.

        Returns:
            The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        return super().download(url, file_path, binary=False, progress_observer=progress_observer)

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
            # Use the built-in 'xml' parser since DICOM files and cell values are well-formed XHTML.
            # "html.parser" is fine for XHTML but unreliable for strict XML.
            # "lxml" defaults to HTML mode and generates a warning for XML.
            # "lxml-xml" forces XML parsing but adds the lxml dependency.
            dom = BeautifulSoup(content, features="xml") 
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
