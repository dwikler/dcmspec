"""Tests for the DOMSectionSpecParser class in dcmspec.dom_section_spec_parser."""
import pytest
from anytree import Node
from dcmspec.dom_section_spec_parser import DOMSectionSpecParser

# Import sample DOM with sections fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_sections import (
    docbook_sample_section_dom,  # noqa: F401
    docbook_sample_section_with_variablelist_dom,  # noqa: F401
    docbook_grouping_section_dom,  # noqa: F401
    docbook_module_definition_section_dom,  # noqa: F401
    docbook_attribute_description_sections_dom,  # noqa: F401
    docbook_sample_section_missing_heading_dom,  # noqa: F401
)


def test_parse_section_returns_own_content_as_html(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_section returns the section's own content as one HTML string, in order."""
    parser = DOMSectionSpecParser()
    content = parser.parse_section(docbook_sample_section_dom, "sect_SAMPLE")
    assert content.name == "content"
    html = content.html
    # Both paragraphs, the note, and the figure are present, in document order
    assert html.index("First paragraph") < html.index("for further explanation")
    assert html.index("for further explanation") < html.index("A caveat worth keeping")
    assert html.index("A caveat worth keeping") < html.index("PS3.3_SAMPLE-1.svg")
    # Inline formatting and links are preserved as raw HTML, not flattened
    assert "<strong>sample</strong>" in html
    assert '<a class="xref" href="#sect_OTHER"' in html
    # The note's own "Note" label is kept (no per-block classification to hang styling off instead)
    assert "Note" in html


def test_parse_section_excludes_heading_and_subsection_but_keeps_tables(
    docbook_sample_section_dom,  # noqa: F811
):
    """Test that parse_section excludes the section's own heading and nested subsection, but keeps tables."""
    parser = DOMSectionSpecParser()
    content = parser.parse_section(docbook_sample_section_dom, "sect_SAMPLE")
    assert "Sample Section" not in content.html  # the section's own <h6> title text
    assert "nested subsection" not in content.html
    assert "Section leak" not in content.html
    # A table embedded in the section's own content (e.g. a Defined Terms table) is not an
    # attribute table and is preserved as-is, like any other content
    assert "An informative table, preserved as part of the section." in content.html


def test_parse_section_variablelist_only_content_is_preserved(
    docbook_sample_section_with_variablelist_dom,  # noqa: F811
):
    """Test that a section whose only content is a <div class="variablelist"> is not dropped."""
    parser = DOMSectionSpecParser()
    content = parser.parse_section(docbook_sample_section_with_variablelist_dom, "sect_MODALITY")
    assert "Defined Terms:" in content.html
    assert "Computed Tomography" in content.html
    # A note nested inside one definition's own <dd> stays in context, embedded where it belongs
    assert 'The term "PLAN" denotes planned activities.' in content.html


def test_parse_section_missing_section_raises(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_section raises ValueError if the section is not found."""
    parser = DOMSectionSpecParser()
    with pytest.raises(ValueError):
        parser.parse_section(docbook_sample_section_dom, "sect_NOT_A_SECTION")


def test_parse_metadata_returns_node(docbook_sample_section_dom):  # noqa: F811
    """Test that parse_metadata returns a Node with section_id, title, and version."""
    parser = DOMSectionSpecParser()
    metadata = parser.parse_metadata(docbook_sample_section_dom, "sect_SAMPLE")
    assert isinstance(metadata, Node)
    assert metadata.section_id == "sect_SAMPLE"
    assert metadata.title == "C.7.6.16.2.2.1 Sample Section"
    assert metadata.version == "2025b"


def test_parse_metadata_section_refs_excludes_nested_subsection(docbook_sample_section_dom):  # noqa: F811
    """Test that section_refs includes the section's own refs but not a nested subsection's."""
    parser = DOMSectionSpecParser()
    metadata = parser.parse_metadata(docbook_sample_section_dom, "sect_SAMPLE")
    assert metadata.section_refs == ["sect_OTHER"]


def test_parse_metadata_image_srcs(docbook_sample_section_dom):  # noqa: F811
    """Test that image_srcs lists each image's raw, unresolved src value in document order."""
    parser = DOMSectionSpecParser()
    metadata = parser.parse_metadata(docbook_sample_section_dom, "sect_SAMPLE")
    assert metadata.image_srcs == ["figures/PS3.3_SAMPLE-1.svg"]


def test_parse_section_grouping_section_delegates_to_subsections(docbook_grouping_section_dom):  # noqa: F811
    """Test that a section with no content of its own includes each subsection's heading and content."""
    parser = DOMSectionSpecParser()
    content = parser.parse_section(docbook_grouping_section_dom, "sect_GROUP")
    html = content.html
    # The grouping section's own heading is still excluded
    assert "Sample Attribute Descriptions" not in html
    # Both subsections' headings and content are included, in document order
    assert "C.9.1 First Attribute" in html
    assert "Explanation of the first attribute" in html
    assert html.index("C.9.1 First Attribute") < html.index("Explanation of the first attribute")
    assert html.index("Explanation of the first attribute") < html.index("C.9.2 Second Attribute")
    # sect_GROUP.2 is itself a grouping section: delegation recurses into sect_GROUP.2.1
    assert "C.9.2.1 Second Attribute Detail" in html
    assert "Explanation nested two levels below sect_GROUP" in html


def test_parse_metadata_grouping_section_collects_refs_and_images_from_subsections(
    docbook_grouping_section_dom,  # noqa: F811
):
    """Test that section_refs and image_srcs are gathered from delegated subsections' content."""
    parser = DOMSectionSpecParser()
    metadata = parser.parse_metadata(docbook_grouping_section_dom, "sect_GROUP")
    assert metadata.section_refs == ["sect_OTHER"]
    assert metadata.image_srcs == ["figures/PS3.3_GROUP.1-1.svg"]


def test_parse_metadata_missing_heading_warns_and_returns_none_title(
    docbook_sample_section_missing_heading_dom, caplog  # noqa: F811
):
    """Test that parse_metadata logs a warning and sets title to None if no heading is found."""
    parser = DOMSectionSpecParser()
    with caplog.at_level("WARNING"):
        metadata = parser.parse_metadata(docbook_sample_section_missing_heading_dom, "sect_NO_HEADING")
    assert metadata.title is None
    assert any("No heading found for section id" in record.message for record in caplog.records)


def test_parse_returns_metadata_and_content(docbook_sample_section_dom):  # noqa: F811
    """Test that parse returns both metadata and content nodes, using table_id as the section id."""
    parser = DOMSectionSpecParser()
    metadata, content = parser.parse(docbook_sample_section_dom, table_id="sect_SAMPLE")
    assert metadata.section_id == "sect_SAMPLE"
    assert content.name == "content"
    assert "First paragraph" in content.html


def test_is_attribute_description_false_for_a_module_own_definition(
    docbook_module_definition_section_dom,  # noqa: F811
):
    """Test that a section titled "... Module", with no enclosing section, is not attribute description."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_module_definition_section_dom, "sect_C.MODULE") is False


def test_is_attribute_description_true_nested_under_a_module(
    docbook_attribute_description_sections_dom,  # noqa: F811
):
    """Test that a section nested two levels under a "... Module"-titled ancestor is attribute description."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_attribute_description_sections_dom, "sect_MOD.1.1") is True


def test_is_attribute_description_true_nested_under_a_macro(
    docbook_attribute_description_sections_dom,  # noqa: F811
):
    """Test that a section nested under a "... Macro"-titled ancestor is attribute description."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_attribute_description_sections_dom, "sect_MACRO.1") is True


def test_is_attribute_description_true_nested_under_a_retired_module(
    docbook_attribute_description_sections_dom,  # noqa: F811
):
    """Test that a section nested under a "... Module (Retired)"-titled ancestor is attribute description."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_attribute_description_sections_dom, "sect_RETIRED.1") is True


def test_is_attribute_description_false_for_section_with_no_module_or_macro_ancestor(
    docbook_sample_section_dom,  # noqa: F811
):
    """Test that a section with no enclosing section at all is not attribute description."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_sample_section_dom, "sect_SAMPLE") is False


def test_is_attribute_description_true_for_missing_section(docbook_sample_section_dom):  # noqa: F811
    """Test that a section id not found in the DOM is left for the normal build to report, not excluded here."""
    parser = DOMSectionSpecParser()
    assert parser.is_attribute_description(docbook_sample_section_dom, "sect_NOT_A_SECTION") is True
