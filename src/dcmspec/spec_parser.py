"""Abstract base class for DICOM specification parsers in dcmspec.

Defines the SpecParser interface for parsing in-memory representations of DICOM specifications.
"""
import re
import unicodedata
from abc import ABC, abstractmethod
from anytree import Node
from bs4 import BeautifulSoup
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

    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text using Unicode normalization and regex."""
        # Normalize unicode characters to compatibility form
        cleaned = unicodedata.normalize('NFKC', text)

        # Replace non-breaking spaces and zero-width spaces with regular space
        cleaned = re.sub(r'[\u00a0\u200b]', ' ', cleaned)

        # Replace typographic single quotes with ASCII single quote
        cleaned = re.sub(r'[\u2018\u2019]', "'", cleaned)
        # Replace typographic double quotes with ASCII double quote
        cleaned = re.sub(r'[\u201c\u201d\u00e2\u0080\u009c\u00e2\u0080\u009d]', '"', cleaned)
        # Replace em dash and en dash with hyphen
        cleaned = re.sub(r'[\u2013\u2014]', '-', cleaned)
        # Remove stray \u00c2 character
        cleaned = cleaned.replace('\u00c2', '')

        # Collapse multiple newlines (including those separated by spaces/tabs) into a single newline
        cleaned = re.sub(r'(\n\s*){2,}', '\n', cleaned)

        return cleaned.strip()

    def _version_from_titlepage(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract the version from a `<div class="titlepage"><h2 class="subtitle">` element."""
        titlepage = dom.find("div", class_="titlepage")
        if not titlepage:
            return None
        subtitle = titlepage.find("h2", class_="subtitle")
        return subtitle.text.split()[2] if subtitle else None

    def _version_from_document_release_info(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract the version from a `<span class="documentreleaseinformation">` element."""
        document_release = dom.find("span", class_="documentreleaseinformation")
        return document_release.text.split()[2] if document_release else None
