"""Abstract base class for DICOM specification parsers in dcmspec.

Defines the SpecParser interface for parsing in-memory representations of DICOM specifications.
"""
from abc import ABC, abstractmethod
from anytree import Node
from typing import Optional, Tuple
import logging


class SpecParser(ABC):
    """Abstract base class for DICOM specification parsers.

    Handles DICOM specifications in various in-memory formats (e.g., DOM for XHTML/XML, CSV).
    Subclasses must implement the `parse` method to parse the specification content and build a structured model.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the DICOM Specification parser with an optional logger.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def parse(self, *args, **kwargs) -> Tuple[Node, Node]:
        """Parse the DICOM specification and return metadata and attribute tree nodes.

        Returns:
            Tuple[Node, Node]: The metadata node and the content node.

        """
        pass
