"""Section specification parser class for DICOM standard processing in dcmspec.

Provides the SectionSpecParser class for parsing DICOM explanatory sections (e.g. PS3.3
Section C.7.6.16.2.2.1) from XHTML documents, converting them into structured in-memory
representations using anytree.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from anytree import Node
from bs4 import BeautifulSoup, Tag
import html2text

from dcmspec.spec_parser import SpecParser
from dcmspec.dom_utils import DOMUtils
from dcmspec.progress import ProgressObserver


class SectionSpecParser(SpecParser):
    """Parser for DICOM explanatory sections in XHTML DOM format.

    Provides methods to extract, parse, and structure a DICOM explanatory section (Part 3
    prose and figures) from an XHTML document, returning anytree Node objects as structured
    in-memory representations. Inherits logging from SpecParser.

    Only a section's own direct content is parsed: nested subsections (each their own,
    separately anchored `<div class="section">`) and any attribute table inside the section
    are not included. A subsection is resolved as its own section model only if it is
    itself referenced elsewhere.
    """

    def __init__(self, logger: Optional[Any] = None):
        """Initialize the SectionSpecParser.

        Sets up the parser with an optional logger and a DOMUtils instance for DOM navigation.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        super().__init__(logger=logger)

        self.dom_utils = DOMUtils(logger=self.logger)

    def parse(
        self,
        dom: BeautifulSoup,
        table_id: str,
        column_to_attr: Optional[Dict[int, str]] = None,
        name_attr: Optional[str] = None,
        include_depth: Optional[int] = None,
        progress_observer: Optional[ProgressObserver] = None,
        **kwargs: Any,
    ) -> Tuple[Node, Node]:
        """Parse a DICOM explanatory section's metadata and content from the DOM.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            table_id (str): The section's anchor id, e.g. "sect_C.7.6.16.2.2.1". Named
                `table_id` for interface compatibility with SpecFactory, which calls every
                parser the same way regardless of what kind of model it builds.
            column_to_attr: Unused by this parser; accepted only for SpecFactory interface compatibility.
            name_attr: Unused by this parser; accepted only for SpecFactory interface compatibility.
            include_depth: Unused by this parser; a section's own content is always parsed
                in a single pass. Recursively resolving sections referenced *from* this
                section's content is the caller's (e.g. ModuleSpecBuilder's) responsibility.
            progress_observer: Unused by this parser; a single section is small enough that
                progress reporting isn't meaningful.
            **kwargs: Accepted and ignored, for forward interface compatibility.

        Returns:
            Tuple[Node, Node]: The metadata node and the section content node.

        """
        section_id = table_id
        content = self.parse_section(dom, section_id)
        metadata = self.parse_metadata(dom, section_id)
        return metadata, content

    def parse_metadata(self, dom: BeautifulSoup, section_id: str) -> Node:
        """Parse a section's metadata from the DOM.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            section_id (str): The id of the section to parse, e.g. "sect_C.7.6.16.2.2.1".

        Returns:
            Node: The root node of the tree representation of the section's metadata.

        Raises:
            ValueError: If the section with the given id is not found.

        """
        section_div = self.dom_utils.get_section(dom, section_id)
        if not section_div:
            raise ValueError(f"Section with id '{section_id}' not found.")

        metadata = Node("metadata")
        metadata.section_id = section_id
        metadata.title = self._extract_title(section_div, section_id)
        metadata.version = self._get_version(dom)
        return metadata

    def parse_section(self, dom: BeautifulSoup, section_id: str) -> Node:
        """Parse a section's own content (text and images) from the DOM into a flat block tree.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            section_id (str): The id of the section to parse, e.g. "sect_C.7.6.16.2.2.1".

        Returns:
            Node: The root "content" node, with one child block per paragraph or figure,
                in document order.

        Raises:
            ValueError: If the section with the given id is not found.

        """
        section_div = self.dom_utils.get_section(dom, section_id)
        if not section_div:
            raise ValueError(f"Section with id '{section_id}' not found.")

        root = Node("content")
        for child in section_div.find_all(recursive=False):
            if self._is_titlepage(child) or self._is_subsection(child):
                continue
            if self._is_figure(child):
                self._add_image_block(child, root)
            elif child.name == "p":
                self._add_text_block(child, root)
        return root

    def _extract_title(self, section_div: Tag, section_id: str) -> Optional[str]:
        """Extract a section's heading text, e.g. "C.7.6.16.2.2.1 Timing Parameter Relationships"."""
        anchor = section_div.find("a", id=section_id)
        heading = anchor.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) if anchor else None
        if not heading:
            self.logger.warning(f"No heading found for section id '{section_id}'.")
            return None
        return heading.get_text(strip=True)

    def _add_text_block(self, cell: Tag, root: Node) -> None:
        """Extract a paragraph's text and outgoing section references into a child text block."""
        text = self._extract_text(cell)
        if not text:
            return
        index = len(root.children)
        Node(f"text_{index}", parent=root, text=text, section_refs=self._extract_section_refs(cell))

    def _add_image_block(self, figure: Tag, root: Node) -> None:
        """Extract a `<div class="figure">`'s image source, alt text, and caption into a child image block."""
        img = figure.find("img")
        if not img:
            return
        caption_tag = figure.find("p", class_="title")
        index = len(root.children)
        Node(
            f"image_{index}",
            parent=root,
            image_src=img.get("src"),
            alt=img.get("alt"),
            caption=caption_tag.get_text(strip=True) if caption_tag else None,
        )

    def _extract_section_refs(self, cell: Tag) -> List[str]:
        """Return the section ids of every `<a class="xref" href="#sect_...">` link within a cell."""
        section_refs = []
        for anchor in cell.find_all("a", class_="xref"):
            target = anchor.get("href", "").split("#", 1)[-1]
            if target.startswith("sect_"):
                section_refs.append(target)
        return section_refs

    def _is_titlepage(self, tag: Tag) -> bool:
        """Determine if a tag is a section's own `<div class="titlepage">` heading wrapper."""
        return tag.name == "div" and "titlepage" in (tag.get("class") or [])

    def _is_subsection(self, tag: Tag) -> bool:
        """Determine if a tag is a nested subsection's `<div class="section">`."""
        return tag.name == "div" and "section" in (tag.get("class") or [])

    def _is_figure(self, tag: Tag) -> bool:
        """Determine if a tag is a `<div class="figure">`."""
        return tag.name == "div" and "figure" in (tag.get("class") or [])

    def _extract_text(self, cell: Tag) -> str:
        """Extract and clean readable text from a cell, stripping links and markup."""
        converter = self._create_html2text_converter()
        raw_text = converter.handle(str(cell))
        return self._clean_text(raw_text)

    def _create_html2text_converter(self) -> html2text.HTML2Text:
        """Create and configure an html2text converter for consistent text extraction."""
        converter = html2text.HTML2Text()
        converter.ignore_links = True       # Remove URLs
        converter.ignore_images = True      # Remove image references
        converter.ignore_emphasis = True    # Remove Markdown emphasis
        converter.body_width = 0            # Disable word wrapping
        return converter

    def _clean_text(self, text: str) -> str:
        """Clean extracted text using Unicode normalization and regex."""
        cleaned = unicodedata.normalize("NFKC", text)
        cleaned = re.sub(r"[\u00a0\u200b]", " ", cleaned)  # nbsp, zero-width space
        cleaned = re.sub(r"[\u2018\u2019]", "'", cleaned)  # typographic single quotes
        cleaned = re.sub(r'[\u201c\u201d]', '"', cleaned)  # typographic double quotes
        cleaned = re.sub(r"[\u2013\u2014]", "-", cleaned)  # en/em dash
        cleaned = re.sub(r"(\n\s*){2,}", "\n", cleaned)  # collapse blank lines
        return cleaned.strip()

    def _get_version(self, dom: BeautifulSoup) -> str:
        """Retrieve the DICOM Standard version from the DOM."""
        version = self._version_from_book(dom) or self._version_from_section(dom)
        if not version:
            self.logger.warning("DICOM Standard version not found")
            return ""
        return version

    def _version_from_book(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract version of DICOM books in HTML format."""
        titlepage = dom.find("div", class_="titlepage")
        if not titlepage:
            return None
        subtitle = titlepage.find("h2", class_="subtitle")
        return subtitle.text.split()[2] if subtitle else None

    def _version_from_section(self, dom: BeautifulSoup) -> Optional[str]:
        """Extract version of DICOM sections in the CHTML format."""
        document_release = dom.find("span", class_="documentreleaseinformation")
        return document_release.text.split()[2] if document_release else None
