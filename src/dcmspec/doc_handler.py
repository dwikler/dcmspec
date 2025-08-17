"""Base class for handling DICOM specification documents in dcmspec.

Provides the DocHandler class for reading, parsing, and downloading DICOM documents
in various formats (e.g., XHTML, PDF). The base class supplies a generic download
method for both text and binary files, and defines the interface for document parsing.
Subclasses should implement the `load_document` method for their specific format.
"""
import os
from typing import Any, Optional
import logging
import requests

from dcmspec.config import Config
from dcmspec.progress import Progress, ProgressObserver, calculate_percent
# BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
from dcmspec.progress import ProgressStatus, handle_legacy_callback
from typing import Callable
# END LEGACY SUPPORT

class DocHandler:
    """Base class for DICOM document handlers.

    Handles DICOM documents in various formats (e.g., XHTML, PDF).
    Subclasses must implement the `load_document` method to handle
    reading/parsing input files. The base class provides a generic
    download method for both text and binary files.

    Progress Reporting:
    The observer pattern is used for progress reporting. Subclasses may extend
    the Progress class and use the progress_observer to report additional information
    (e.g., status, errors, or other context) beyond percent complete, enabling future
    extensibility for richer progress tracking.
    """

    def __init__(self, config: Optional[Config] = None, logger: Optional[logging.Logger] = None):
        """Initialize the document handler with an optional logger.

        Args:
            config (Optional[Config]): Config instance to use. If None, a default Config is created.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        Logging:
            A logger may be passed for custom logging control. If no logger is provided,
            a default logger for this class is used. In both cases, no logging handlers
            are added by default. To see log output, logging should be configured in the
            application (e.g., with logging.basicConfig()).

        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        if config is not None and not isinstance(config, Config):
            raise TypeError("config must be an instance of Config or None")
        self.config = config or Config()

    def download(
        self,
        url: str,
        file_path: str,
        binary: bool = False,
        progress_observer: 'Optional[ProgressObserver]' = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: 'Optional[Callable[[int], None]]' = None
        # END LEGACY SUPPORT
    ) -> str:
        """Download a file from a URL and save it to the specified path.

        Args:
            url (str): The URL to download the file from.
            file_path (str): The path to save the downloaded file.
            binary (bool): If True, save as binary. If False, save as UTF-8 text.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.

        Returns:
            str: The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        self.logger.info(f"Downloading document from {url} to {file_path}")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create directory for {file_path}: {e}")
            raise RuntimeError(f"Failed to create directory for {file_path}: {e}") from e
        try:
            with requests.get(url, timeout=30, stream=True, headers={"Accept-Encoding": "identity"}) as response:
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))
                chunk_size = 8192
                if binary:
                    self._download_binary(response, file_path, total, chunk_size, progress_observer)
                else:
                    self._download_text(response, file_path, total, chunk_size, progress_observer)
            self.logger.info(f"Document downloaded to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            raise RuntimeError(f"Failed to download {url}: {e}") from e
        except OSError as e:
            self.logger.error(f"Failed to save file {file_path}: {e}")
            raise RuntimeError(f"Failed to save file {file_path}: {e}") from e

    def _report_progress(self, downloaded, total, progress_observer, last_percent):
        """Report progress if percent changed.

        If the total file size is unknown or invalid, calls the observer with -1 to indicate
        indeterminate progress. Otherwise, calls the observer with the integer percent (0-100).
        Adds status=ProgressStatus.DOWNLOADING to all progress events.
        """
        if not progress_observer:
            return

        percent = calculate_percent(downloaded, total)
        if percent != last_percent[0]:
            progress_observer(Progress(percent, status=ProgressStatus.DOWNLOADING))
            last_percent[0] = percent

    def _download_binary(self, response, file_path, total, chunk_size, progress_observer):
        """Download and save a binary file with progress reporting.

        Streams each chunk directly to the file to avoid high memory usage.
        Reports progress using the provided observer.
        """
        downloaded = 0
        last_percent = [None]
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    # For binary, no cleaning is needed
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._report_progress(downloaded, total, progress_observer, last_percent)

    def _download_text(self, response, file_path, total, chunk_size, progress_observer):
        """Download and save a text file with progress reporting.

        Streams cleaned chunks directly to the file to avoid high memory usage.
        Reports progress using the provided observer using response.encoding if available
        for accurate byte counting.
        """
        downloaded = 0
        last_percent = [None]
        encoding = response.encoding or "utf-8"
        with open(file_path, "w", encoding="utf-8") as f:
            for chunk in response.iter_content(chunk_size=chunk_size, decode_unicode=True):
                if chunk:
                    cleaned_chunk = self.clean_text(chunk)
                    f.write(cleaned_chunk)
                    chunk_bytes = cleaned_chunk.encode(encoding)
                    downloaded += len(chunk_bytes)
                    self._report_progress(downloaded, total, progress_observer, last_percent)

    def clean_text(self, text: str) -> str:
        """Clean text content before saving.

        Subclasses can override this to perform format-specific cleaning (e.g., remove ZWSP/NBSP for XHTML).
        By default, returns the text unchanged.

        Args:
            text (str): The text content to clean.

        Returns:
            str: The cleaned text.

        """
        return text

    def load_document(
        self,
        cache_file_name: str,
        url: Optional[str] = None,
        force_download: bool = False,
        progress_observer: 'Optional[ProgressObserver]' = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: 'Optional[Callable[[int], None]]' = None,
        # END LEGACY SUPPORT
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Implement this method to read and parse the document file, returning a parsed object.

        Subclasses should implement this method to load and parse a document file
        (e.g., XHTML, PDF, CSV) and return a format-specific parsed object.
        The exact type of the returned object depends on the subclass
        (e.g., BeautifulSoup for XHTML, pdfplumber.PDF for PDF).

        Args:
            cache_file_name (str): Path or name of the local cached file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool, optional): If True, download the file even if it exists locally.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.
            *args: Additional positional arguments for format-specific loading.
            **kwargs: Additional keyword arguments for format-specific loading.

        Returns:
            Any: The parsed document object (type depends on subclass).

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        raise NotImplementedError("Subclasses must implement load_document()")
