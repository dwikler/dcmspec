from abc import ABC, abstractmethod
import logging
from typing import Optional


class SpecParser(ABC):
    """
    Abstract base class for DICOM specification parsers.

    The DICOM Specification may be in various formats (e.g., DOM, CSV, etc.).
    Subclasses must implement the `parse` method to parse specification contents and build
    a representation of the specification metadata and content.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the DICOM Specification parser with an optional logger.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def parse_table(self, source):
        """
        Parses a DICOM Specification from source data.

        Args:
            source : DICOM Specification data.
        """
        pass
