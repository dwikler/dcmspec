from typing import Any, Optional
import logging
from abc import ABC, abstractmethod

from dcmspec.config import Config


class DocHandler(ABC):
    """
    Abstract base class for DICOM document handlers.

    The DICOM documents may be in various formats (e.g., XHTML, XML, etc.).
    Subclasses must implement the `read_dom` and `download` methods to handle
    reading/parsing input files and downloading files from URLs.
    """

    def __init__(self, config: Optional[Config] = None, logger: Optional[logging.Logger] = None):
        """
        Initializes the document handler with an optional logger.

        Args:
            config (Optional[Config]): Config instance to use. If None, a default Config is created.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Set the default logging level to INFO
        self.logger.setLevel(logging.INFO)

        # Create a console handler and set its level to INFO
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Add the handler to the logger
        self.logger.addHandler(console_handler)

        if config is not None and not isinstance(config, Config):
            raise TypeError("config must be an instance of Config or None")
        self.config = config or Config()

    @abstractmethod
    def get_dom(self, file_path: str) -> Any:
        """
        Reads and parses the document file, returning a DOM object.

        Args:
            file_path (str): Path to the document file.

        Returns:
            Any: The parsed DOM object.
        """
        pass

    @abstractmethod
    def download(self, url: str, file_path: str) -> None:
        """
        Downloads the file from a URL and saves it to the specified path.

        Args:
            url (str): The URL to download the file from.
            file_path (str): The path to save the downloaded file.
        """
        pass
