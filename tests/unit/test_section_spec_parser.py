"""Tests for the SectionSpecParser class in dcmspec.section_spec_parser."""
import pytest
from anytree import Node
from dcmspec.section_spec_parser import SectionSpecParser

# Import sample DOM with sections fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_sections import (
    docbook_sample_section_dom,  # noqa: F401
    docbook_sample_section_missing_heading_dom,  # noqa: F401
)


def test_parse_section_returns_flat_blocks_in_order(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_section returns text and image blocks in document order, excluding subsections."""
    parser = SectionSpecParser()
    content = parser.parse_section(docbook_sample_section_dom, "sect_SAMPLE")
    children = list(content.children)
    assert len(children) == 3
    assert children[0].name == "text_0"
    assert children[0].text == "First paragraph of the sample section."
    assert children[0].section_refs == []
    assert children[1].name == "text_1"
    assert "for further explanation." in children[1].text
    assert children[1].section_refs == ["sect_OTHER"]
    assert children[2].name == "image_2"
    assert children[2].image_src == "figures/PS3.3_SAMPLE-1.svg"
    assert children[2].alt == "Sample Figure"
    assert children[2].caption == "Figure SAMPLE-1. Sample Figure"


def test_parse_section_excludes_nested_subsection_content(docbook_sample_section_dom):  # noqa: F811
    """Test that a nested subsection's own paragraph is not included when parsing the parent section."""
    parser = SectionSpecParser()
    content = parser.parse_section(docbook_sample_section_dom, "sect_SAMPLE")
    all_text = " ".join(getattr(child, "text", "") for child in content.children)
    assert "nested subsection" not in all_text


def test_parse_section_missing_section_raises(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_section raises ValueError if the section is not found."""
    parser = SectionSpecParser()
    with pytest.raises(ValueError):
        parser.parse_section(docbook_sample_section_dom, "sect_NOT_A_SECTION")


def test_parse_metadata_returns_node(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_metadata returns a Node with section_id, title, and version."""
    parser = SectionSpecParser()
    metadata = parser.parse_metadata(docbook_sample_section_dom, "sect_SAMPLE")
    assert isinstance(metadata, Node)
    assert metadata.section_id == "sect_SAMPLE"
    assert metadata.title == "C.7.6.16.2.2.1 Sample Section"
    assert metadata.version == "2025b"


def test_parse_metadata_missing_heading_warns_and_returns_none_title(
    docbook_sample_section_missing_heading_dom, caplog  # noqa: F811
):
    """Test that parse_metadata logs a warning and sets title to None if no heading is found."""
    parser = SectionSpecParser()
    with caplog.at_level("WARNING"):
        metadata = parser.parse_metadata(docbook_sample_section_missing_heading_dom, "sect_NO_HEADING")
    assert metadata.title is None
    assert any("No heading found for section id" in record.message for record in caplog.records)


def test_parse_returns_metadata_and_content(docbook_sample_section_dom):  # noqa: F811
    """Test that parse returns both metadata and content nodes, using table_id as the section id."""
    parser = SectionSpecParser()
    metadata, content = parser.parse(docbook_sample_section_dom, table_id="sect_SAMPLE")
    assert metadata.section_id == "sect_SAMPLE"
    assert content.name == "content"
    assert len(content.children) == 3
