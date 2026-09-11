"""Section specification parser class for DICOM standard processing in dcmspec.

Provides the DOMSectionSpecParser class for parsing a DICOM standard section (e.g. PS3.3
Section C.7.6.16.2.2.1) from an XHTML document, converting it into an in-memory
representation using anytree.
"""
from typing import Any, Dict, List, Optional, Tuple

from anytree import Node
from bs4 import BeautifulSoup, Tag

from dcmspec.spec_parser import SpecParser
from dcmspec.dom_utils import DOMUtils
from dcmspec.progress import ProgressObserver


class DOMSectionSpecParser(SpecParser):
    """Parser for a DICOM standard section, given its anchor id.

    A section's content stays document-based: captured as a single HTML string, as-is,
    not broken into structured fields.

    If a section has no content of its own, only subsections (e.g. a "... Attribute
    Descriptions" grouping section), each subsection's heading and content is included
    recursively. Otherwise, subsections are skipped.

    A section's content may itself link to other sections (e.g. "See Section C.x").
    Those references are listed on metadata.section_refs so the caller can decide whether
    to resolve them or not.
    """

    def __init__(self, logger: Optional[Any] = None):
        """Initialize the DOMSectionSpecParser.

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
        """Parse a DICOM standard section's metadata and content from the DOM.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            table_id (str): The section's anchor id, e.g. "sect_C.7.6.16.2.2.1". Named
                `table_id` for interface compatibility with SpecFactory, which calls every
                parser the same way regardless of what kind of model it builds.
            column_to_attr: Unused by this parser; accepted only for SpecFactory interface compatibility.
            name_attr: Unused by this parser; accepted only for SpecFactory interface compatibility.
            include_depth: Unused by this parser; a section's content is always parsed
                in a single pass. It does not resolve referenced sections.
            progress_observer: Unused by this parser; assuming a single section is small enough that
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
            Node: The root node of the tree representation of the section's metadata, with
                `section_id`, `title`, `version`, `section_refs`, and `image_srcs` attributes.

        Raises:
            ValueError: If the section with the given id is not found.

        """
        section_div = self.dom_utils.get_section(dom, section_id)
        if not section_div:
            raise ValueError(f"Section with id '{section_id}' not found.")
        children = self._resolved_content_children(section_div)

        metadata = Node("metadata")
        metadata.section_id = section_id
        metadata.title = self._extract_title(section_div, section_id)
        metadata.version = self._get_version(dom)
        metadata.section_refs = [ref for child in children for ref in self._extract_section_refs(child)]
        metadata.image_srcs = [
            src for child in children for img in child.find_all("img") for src in [img.get("src")] if src
        ]
        return metadata

    def parse_section(self, dom: BeautifulSoup, section_id: str) -> Node:
        """Parse a section's content into a single HTML string on the content node.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object.
            section_id (str): The id of the section to parse, e.g. "sect_C.7.6.16.2.2.1".

        Returns:
            Node: The root "content" node, with a single `html` attribute holding the section's HTML.

        Raises:
            ValueError: If the section with the given id is not found.

        """
        section_div = self.dom_utils.get_section(dom, section_id)
        if not section_div:
            raise ValueError(f"Section with id '{section_id}' not found.")
        children = self._resolved_content_children(section_div)
        html = self._clean_extracted_text("".join(str(child) for child in children))
        return Node("content", html=html)

    def _own_content_children(self, section_div: Tag) -> List[Tag]:
        """Return section_div's direct children, excluding its heading and nested subsections."""
        return [
            child for child in section_div.find_all(recursive=False)
            if not (self._is_titlepage(child) or self._is_subsection(child))
        ]

    def _resolved_content_children(self, section_div: Tag) -> List[Tag]:
        """Return the tags making up a section's content, delegating to subsections if it has no own content."""
        own_children = self._own_content_children(section_div)
        if "".join(str(child) for child in own_children).strip():
            return own_children

        subsections = [child for child in section_div.find_all(recursive=False) if self._is_subsection(child)]
        if not subsections:
            return own_children

        delegated: List[Tag] = []
        for subsection in subsections:
            heading = subsection.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if heading is not None:
                delegated.append(heading)
            delegated.extend(self._resolved_content_children(subsection))
        return delegated

    def _extract_title(self, section_div: Tag, section_id: str) -> Optional[str]:
        """Extract a section's heading text, e.g. "C.7.6.16.2.2.1 Timing Parameter Relationships"."""
        anchor = section_div.find("a", id=section_id)
        heading = anchor.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) if anchor else None
        if not heading:
            self.logger.warning(f"No heading found for section id '{section_id}'.")
            return None
        return heading.get_text(strip=True)

    def _extract_section_refs(self, tag: Tag) -> List[str]:
        """Return the section ids of every `<a class="xref" href="#sect_...">` link within a tag."""
        section_refs = []
        for anchor in tag.find_all("a", class_="xref"):
            target = anchor.get("href", "").split("#", 1)[-1]
            if target.startswith("sect_"):
                section_refs.append(target)
        return section_refs

    def _is_titlepage(self, tag: Tag) -> bool:
        """Determine if a tag is a section's `<div class="titlepage">` heading wrapper."""
        return tag.name == "div" and "titlepage" in (tag.get("class") or [])

    def _is_subsection(self, tag: Tag) -> bool:
        """Determine if a tag is a nested subsection's `<div class="section">`."""
        return tag.name == "div" and "section" in (tag.get("class") or [])

    def _get_version(self, dom: BeautifulSoup) -> str:
        """Retrieve the DICOM Standard version from the DOM."""
        version = self._version_from_titlepage(dom) or self._version_from_document_release_info(dom)
        if not version:
            self.logger.warning("DICOM Standard version not found")
            return ""
        return version
