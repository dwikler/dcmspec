"""Tests for the DOMTableSpecParser class in dcmspec.dom_table_spec_parser."""
import pytest
from anytree import Node
from bs4 import BeautifulSoup
from dcmspec.dom_table_spec_parser import DOMTableSpecParser

# Import sample DOM with tables fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_tables import (
    docbook_sample_dom_1,  # noqa: F401
    docbook_sample_dom_2,  # noqa: F401
    table_colspan_dom,  # noqa: F401
    table_rowspan_dom,  # noqa: F401
    table_colspan_rowspan_dom, # noqa: F401
    table_include_dom,  # noqa: F401
)

def test_parse_table_returns_node(docbook_sample_dom_1):  # noqa: F811
    """Test that parse_table returns a Node with correct children and sanitized names."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    node = parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name"
    )
    children = list(node.children)
    assert len(children) == 2
    assert children[0].elem_name == "Attr Name (Tést)"
    assert children[0].name == "attr_name_-test-"  # sanitized string
    assert children[0].elem_tag == "(0101,0001)"
    assert children[0].elem_type == "1"
    assert children[0].elem_desc == "Desc1"
    assert children[1].elem_name == "AttrName2"
    assert children[1].name == "attrname2"
    assert children[1].elem_tag == "(0101,0002)"
    assert children[1].elem_type == "2"
    assert children[1].elem_desc == "Desc2"

@pytest.mark.parametrize(
    "fixture_name, expected_version",
    [
        ("docbook_sample_dom_1", "2025b"),
        ("docbook_sample_dom_2", "2025b"),
    ]
)
def test_parse_metadata_returns_node(request, fixture_name, expected_version):
    """Test that parse_metadata returns a Node with version and header."""
    parser = DOMTableSpecParser()
    dom = request.getfixturevalue(fixture_name)
    column_to_attr = {0: "elem_name", 1: "elem_tag"}
    node = parser.parse_metadata(
        dom=dom,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr
    )
    assert isinstance(node, Node)
    assert hasattr(node, "version")
    assert hasattr(node, "header")
    assert node.version == expected_version
    assert node.header == ["Attr Name", "Tag"]

def test_parse_table_missing_table_raises(docbook_sample_dom_1):  # noqa: F811
    """Test that parse_table raises ValueError if table is not found."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag"}
    with pytest.raises(ValueError):
        parser.parse_table(
            dom=docbook_sample_dom_1,
            table_id="not_a_table",
            column_to_attr=column_to_attr,
            name_attr="elem_name"
        )

def test_parse_table_missing_column_to_attr_raises(docbook_sample_dom_1):  # noqa: F811
    """Test that parse_table raises ValueError if column_to_attr is missing."""
    parser = DOMTableSpecParser()
    with pytest.raises(ValueError):
        parser.parse_table(
            dom=docbook_sample_dom_1,
            table_id="test_table",
            column_to_attr={},
            name_attr="elem_name"
        )

def test_parse_returns_metadata_and_content(docbook_sample_dom_1):  # noqa: F811
    """Test that parse returns a tuple of (metadata, content) nodes."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    metadata, content = parser.parse(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name"
    )
    assert isinstance(metadata, Node)
    assert isinstance(content, Node)
    assert hasattr(metadata, "header")
    assert hasattr(metadata, "version")
    assert metadata.version == "2025b"
    children = list(content.children)
    assert len(children) == 2
    assert children[0].name == "attr_name_-test-"  # sanitized string
    assert children[1].elem_name == "AttrName2"



def test_parse_table_colspan(table_colspan_dom):  # noqa: F811
    """Test parse_table handles colspan correctly."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3"}
    node = parser.parse_table(
        dom=table_colspan_dom,
        table_id="table_COLSPAN",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    assert len(children) == 1
    assert children[0].col1 == "A"
    # col2 is skipped due to colspan, col3 is B
    assert children[0].col3 == "B"

def test_parse_table_rowspan(table_rowspan_dom):  # noqa: F811
    """Test parse_table handles rowspan correctly."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2"}
    node = parser.parse_table(
        dom=table_rowspan_dom,
        table_id="table_ROWSPAN",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    assert len(children) == 2
    assert children[0].col1 == "A"
    assert children[0].col2 == "B"
    assert children[1].col1 == "A"  # from rowspan
    assert children[1].col2 == "C"

def test_parse_table_colspan_rowspan(table_colspan_rowspan_dom):  # noqa: F811
    """Test parse_table handles both colspan and rowspan together."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3"}
    node = parser.parse_table(
        dom=table_colspan_rowspan_dom,
        table_id="table_COLSPANROWSPAN",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    assert len(children) == 2
    assert children[0].col1 == "A"
    assert children[0].col3 == "B"
    assert children[1].col1 == "A"  # from rowspan+colspan
    assert children[1].col3 == "C"


def test_parse_table_include_triggers_recursion(table_include_dom):  # noqa: F811
    """Test that parse_table handles an 'Include' row and recursively parses the included table."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3", 3: "col4"}
    node = parser.parse_table(
        dom=table_include_dom,
        table_id="table_MAIN",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    # The root should have 4 children: AttrName1, AttrName2, AttrName10, AttrName11
    assert len(children) == 4
    assert children[0].col1 == "AttrName1"
    assert children[1].col1 == "AttrName2"
    assert children[2].col1 == "AttrName10"
    assert children[3].col1 == "AttrName11"

def test_parse_table_include_with_gt_nests_under_previous(table_include_dom):  # noqa: F811
    """Test that parse_table nests included table rows under the previous node if '>' is present before Include."""
    # Modify the fixture to use '>Include' instead of 'Include'
    html = str(table_include_dom)
    html = html.replace("Include <a", "&gt;Include <a")
    dom = BeautifulSoup(html, "lxml-xml")
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3", 3: "col4"}
    node = parser.parse_table(
        dom=dom,
        table_id="table_MAIN",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    # The root should have 2 children: AttrName1 and AttrName2
    assert len(children) == 2
    assert children[0].col1 == "AttrName1"
    assert children[1].col1 == "AttrName2"
    # The included table rows should be children of AttrName2
    included_children = list(children[1].children)
    assert len(included_children) == 2
    assert included_children[0].col1 == ">AttrName10"
    assert included_children[1].col1 == ">AttrName11"

def test_parse_table_include_missing_table(table_include_dom):  # noqa: F811
    """Test that parse_table raises ValueError when an 'Include' row references a non-existent table."""
    parser = DOMTableSpecParser()
    dom = table_include_dom

    # Find the "Include" row (the one with colspan=4)
    include_row = dom.find("td", {"colspan": "4"}).parent
    # Find the <a class="xref"> in that row and change its href to a non-existent table
    include_anchor = include_row.find("a", {"class": "xref"})
    include_anchor["href"] = "#non_existent_table"

    column_to_attr = {0: "col1", 1: "col2", 2: "col3", 3: "col4"}
    with pytest.raises(ValueError):
        parser.parse_table(
            dom=dom,
            table_id="table_MAIN",
            column_to_attr=column_to_attr,
            name_attr="col1"
        )
