"""Base class for handling DICOM specification documents in dcmspec.

Provides the DocHandler class for reading, parsing, and downloading DICOM documents
in various formats (e.g., XHTML, PDF). The base class supplies a generic download
method for both text and binary files, and defines the interface for document parsing.
Subclasses should implement the `load_document` method for their specific format.
"""
import os
from typing import Any, Optional
import logging

from dcmspec.config import Config


class DocHandler:
    """Base class for DICOM document handlers.

    Handles DICOM documents in various formats (e.g., XHTML, PDF).
    Subclasses must implement the `load_document` method to handle
    reading/parsing input files. The base class provides a generic
    download method for both text and binary files.
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

    def download(self, url: str, file_path: str, binary: bool = False) -> str:
        """Download a file from a URL and save it to the specified path.

        Downloads a file from the given URL and saves it to the specified file path.
        By default, saves as text (UTF-8); if binary is True, saves as binary (for PDFs, images, etc).
        Subclasses may override this method or the `clean_text` hook for format-specific processing.

        Args:
            url (str): The URL to download the file from.
            file_path (str): The path to save the downloaded file.
            binary (bool): If True, save as binary. If False, save as UTF-8 text.

        Returns:
            str: The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        import requests
        self.logger.info(f"Downloading document from {url} to {file_path}")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create directory for {file_path}: {e}")
            raise RuntimeError(f"Failed to create directory for {file_path}: {e}") from e
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            if binary:
                with open(file_path, "wb") as f:
                    f.write(response.content)
            else:
                content = response.text
                content = self.clean_text(content)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            self.logger.info(f"Document downloaded to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            raise RuntimeError(f"Failed to download {url}: {e}") from e
        except OSError as e:
            self.logger.error(f"Failed to save file {file_path}: {e}")
            raise RuntimeError(f"Failed to save file {file_path}: {e}") from e

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
            *args: Additional positional arguments for format-specific loading.
            **kwargs: Additional keyword arguments for format-specific loading.

        Returns:
            Any: The parsed document object (type depends on subclass).

        """
        raise NotImplementedError("Subclasses must implement load_document()")
