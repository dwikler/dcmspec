"""Tests for the DOMTableSpecParser class in dcmspec.dom_table_spec_parser."""
import pytest
from anytree import Node
from bs4 import BeautifulSoup
from dcmspec.dom_table_spec_parser import DOMTableSpecParser

# Import sample DOM with tables fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_tables import (
    docbook_sample_dom_1,  # noqa: F401
    docbook_sample_dom_2,  # noqa: F401
    table_empty_rows_and_cells_dom,  # noqa: F401
    table_colspan_dom,  # noqa: F401
    table_mixed_colspan_dom,  # noqa: F401
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

def test_parse_table_unformatted_false_returns_html(docbook_sample_dom_1):  # noqa: F811
    """Test that setting unformatted_list with False for a column returns the HTML for that column."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    # Set unformatted_list so that column 3 (elem_desc) returns HTML, others return text
    unformatted_list = [True, True, True, False]
    node = parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        unformatted_list=unformatted_list
    )
    children = list(node.children)
    assert len(children) == 2
    # elem_name should be plain text
    assert children[0].elem_name == "Attr Name (Tést)"
    # elem_desc should be the exact HTML for the cell
    expected_html = '<p>Desc1</p>'
    assert children[0].elem_desc.strip() == expected_html
    expected_html2 = '<p>Desc2</p>'
    assert children[1].elem_desc.strip() == expected_html2

def test_parse_table_warns_and_forces_unformatted_true_for_name_attr(docbook_sample_dom_1, caplog):  # noqa: F811
    """Test that parse_table forces unformatted=True for the name_attr column and logs a warning if set to False."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    # Set unformatted_list so that column 0 (elem_name, the name_attr) is False, others are True
    unformatted_list = [False, True, True, True]
    with caplog.at_level("WARNING"):
        node = parser.parse_table(
            dom=docbook_sample_dom_1,
            table_id="table_SAMPLE",
            column_to_attr=column_to_attr,
            name_attr="elem_name",
            unformatted_list=unformatted_list
        )
    children = list(node.children)
    # elem_name should still be plain text, not HTML
    assert children[0].elem_name == "Attr Name (Tést)"
    assert children[1].elem_name == "AttrName2"
    # There should be a warning in the logs
    assert any(
        "unformatted=False for name_attr column 'elem_name'" in record.message
        for record in caplog.records
    )

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

def test_parse_table_extra_column_to_attr(docbook_sample_dom_1):  # noqa: F811
    """Test parse_table handles extra items in column_to_attr (more than in the DOM table)."""
    parser = DOMTableSpecParser()
    # The DOM has 4 columns, but we add a 5th mapping
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc", 4: "extra_col"}
    node = parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name"
    )
    children = list(node.children)
    assert len(children) == 2
    # The extra_col should be None for all rows
    assert hasattr(children[0], "extra_col")
    assert children[0].extra_col is None
    assert hasattr(children[1], "extra_col")
    assert children[1].extra_col is None

def test_parse_table_fewer_column_to_attr(docbook_sample_dom_1):  # noqa: F811
    # sourcery skip: extract-duplicate-method
    """Test parse_table handles fewer items in column_to_attr (less than in the DOM table)."""
    parser = DOMTableSpecParser()
    # The DOM has 4 columns, but we only map 2
    column_to_attr = {0: "elem_name", 1: "elem_tag"}
    node = parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name"
    )
    children = list(node.children)
    assert len(children) == 2
    assert hasattr(children[0], "elem_name")
    assert hasattr(children[0], "elem_tag")
    assert not hasattr(children[0], "elem_type")
    assert not hasattr(children[0], "elem_desc")
    assert hasattr(children[1], "elem_name")
    assert hasattr(children[1], "elem_tag")
    assert not hasattr(children[1], "elem_type")
    assert not hasattr(children[1], "elem_desc")

def test_parse_table_empty_rows_and_cells(table_empty_rows_and_cells_dom):  # noqa: F811
    """Test parse_table handles empty rows and empty cells gracefully."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2"}
    node = parser.parse_table(
        dom=table_empty_rows_and_cells_dom,
        table_id="table_EMPTY",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    # The first row is empty and should be skipped (no name_attr)
    assert len(children) == 2
    assert children[0].col1 == ""
    assert children[0].col2 == "Value2"
    assert children[1].col1 == "Value3"
    assert children[1].col2 == ""

def test_parse_table_colspan(table_colspan_dom):  # noqa: F811
    """Test parse_table handles colspan correctly and missing columns are set to None if skip_columns is not set."""
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
    # col2 is missing in this row, so should be present as None
    assert hasattr(children[0], "col2")
    assert children[0].col2 is None
    assert children[0].col3 == "B"

def test_parse_table_mixed_colspan(table_mixed_colspan_dom):  # noqa: F811
    """Test parse_table with a DOM where some rows have a missing column (colspan) and others do not."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3"}
    node = parser.parse_table(
        dom=table_mixed_colspan_dom,
        table_id="table_MIXED",
        column_to_attr=column_to_attr,
        name_attr="col1"
    )
    children = list(node.children)
    assert len(children) == 2
    # First row: col1="A", col2=None, col3="B"
    assert children[0].col1 == "A"
    assert hasattr(children[0], "col2")
    assert children[0].col2 is None
    assert children[0].col3 == "B"
    # Second row: col1="C", col2="D", col3="E"
    assert children[1].col1 == "C"
    assert children[1].col2 == "D"
    assert children[1].col3 == "E"

def test_parse_table_skip_columns_all_cells_not_in_dom(docbook_sample_dom_1):  # noqa: F811
    """Test parse_table with skip_columns skips a column that is not present in the DOM at all (no colspan)."""
    parser = DOMTableSpecParser()
    # Add a non-existent column (index 4) to column_to_attr
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc", 4: "missing_col"}
    metadata, node = parser.parse(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        skip_columns=[4]
    )
    children = list(node.children)
    assert len(children) == 2
    assert children[0].elem_name == "Attr Name (Tést)"
    assert children[0].elem_tag == "(0101,0001)"
    assert children[0].elem_type == "1"
    assert children[0].elem_desc == "Desc1"
    assert not hasattr(children[0], "missing_col")
    assert children[1].elem_name == "AttrName2"
    assert children[1].elem_tag == "(0101,0002)"
    assert children[1].elem_type == "2"
    assert children[1].elem_desc == "Desc2"
    assert not hasattr(children[1], "missing_col")
    # The header should not include the missing column
    assert metadata.header == ["Attr Name", "Tag", "Type", "Description"]
    # The column_to_attr should not include the missing column
    assert metadata.column_to_attr == {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}

def test_parse_table_skip_columns_column_present_not_skipped(docbook_sample_dom_1):  # noqa: F811
    """Test that specifying skip_columns for a column that is present in the DOM does NOT skip it."""
    parser = DOMTableSpecParser()
    # All columns are present in the DOM, but we specify skip_columns for column 2 ("elem_type")
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    node = parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        skip_columns=[2],  # "elem_type" is present in the DOM, so should NOT be skipped
    )
    children = list(node.children)
    assert len(children) == 2
    # "elem_type" should be present and have the correct value
    assert hasattr(children[0], "elem_type")
    assert children[0].elem_type == "1"
    assert hasattr(children[1], "elem_type")
    assert children[1].elem_type == "2"

def test_parse_table_skip_columns_all_cells_colspan(table_colspan_dom):  # noqa: F811
    """Test parse_table with skip_columns skips columns for all rows when all cells are missing that column."""
    parser = DOMTableSpecParser()
    # Simulate a table where col2 is systematically missing (colspan=2 for all rows)
    column_to_attr = {0: "col1", 1: "col2", 2: "col3"}
    node = parser.parse_table(
        dom=table_colspan_dom,
        table_id="table_COLSPAN",
        column_to_attr=column_to_attr,
        name_attr="col1",
        skip_columns=[1]
    )
    children = list(node.children)
    assert len(children) == 1
    assert children[0].col1 == "A"
    # col2 should not be present at all
    assert not hasattr(children[0], "col2")
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


def test_parse_table_colspan_rowspan_unformatted(table_colspan_rowspan_dom):  # noqa: F811
    """Test parse_table handles both colspan and rowspan together, and unformatted_list, including HTML alignment."""
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3"}
    # Set unformatted_list so that col3 returns HTML, others return text
    unformatted_list = [True, False, False]
    node = parser.parse_table(
        dom=table_colspan_rowspan_dom,
        table_id="table_COLSPANROWSPAN",
        column_to_attr=column_to_attr,
        name_attr="col1",
        unformatted_list=unformatted_list
    )
    children = list(node.children)
    # Print the actual values for inspection
    print("Row 0:", "col1:", repr(children[0].col1), "col2:", repr(children[0].col2), "col3:", repr(children[0].col3))
    print("Row 1:", "col1:", repr(children[1].col1), "col2:", repr(children[1].col2), "col3:", repr(children[1].col3))
    # There should be 2 rows
    assert len(children) == 2

    # First row: col1="A", col2=None (colspan), col3="<p>B</p>"
    assert children[0].col1 == "A"
    assert hasattr(children[0], "col2")
    assert children[0].col2 is None
    assert children[0].col3.strip() == "<p>B</p>"

    # Second row: col1="A" (from rowspan+colspan), col2=None (colspan), col3="<p><span class=\"foo\">C</span></p>"
    assert children[1].col1 == "A"
    assert hasattr(children[1], "col2")
    assert children[1].col2 is None
    assert children[1].col3.strip() == '<p><span class="foo">C</span></p>'

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
    # sourcery skip: extract-duplicate-method
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

def test_parse_table_include_with_gt_nests_under_previous_html_elem_desc(table_include_dom):  # noqa: F811
    """Test parsing nested structures with unformatted_list is set to False for column 3."""
    # Modify the fixture to use '>Include' instead of 'Include'
    html = str(table_include_dom)
    html = html.replace("Include <a", "&gt;Include <a")
    dom = BeautifulSoup(html, "lxml-xml")
    parser = DOMTableSpecParser()
    column_to_attr = {0: "col1", 1: "col2", 2: "col3", 3: "elem_desc"}
    # Set unformatted_list so that column 3 (elem_desc) returns HTML, others return text
    unformatted_list = [True, True, True, False]
    node = parser.parse_table(
        dom=dom,
        table_id="table_MAIN",
        column_to_attr=column_to_attr,
        name_attr="col1",
        unformatted_list=unformatted_list
    )
    children = list(node.children)
    # The root should have 2 children: AttrName1 and AttrName2 and both should have elem_desc as HTML
    assert len(children) == 2
    assert children[0].col1 == "AttrName1"
    assert children[1].col1 == "AttrName2"
    # The included table rows should be children of AttrName2
    included_children = list(children[1].children)
    assert len(included_children) == 2
    assert included_children[0].col1 == ">AttrName10"
    assert included_children[1].col1 == ">AttrName11"
    # Both levels should have the exact HTML for elem_desc
    assert children[0].elem_desc.strip() == "<p>Desc1</p>"
    assert children[1].elem_desc.strip() == "<p>Desc2</p>"
    assert included_children[0].elem_desc.strip() == "<p>Bla</p>"
    assert included_children[1].elem_desc.strip() == "<p>Bla</p>"

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

def test_parse_metadata_realigns_column_to_attr_when_middle_missing(docbook_sample_dom_1):  # noqa: F811
    """Test that parse realigns the metadata column_to_attr values when a middle column (e.g., elem_type) is missing."""
    parser = DOMTableSpecParser()
    # Simulate a mapping where index 2 (elem_type) is missing, but index 3 (elem_desc) is present
    column_to_attr = {0: "elem_name", 1: "elem_tag", 3: "elem_desc"}
    metadata, _ = parser.parse(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name"
    )
    # The keys may not be realigned, but the values should be in the correct order
    assert list(metadata.column_to_attr.values()) == ["elem_name", "elem_tag", "elem_desc"]
    # The header should have the correct number of columns and order
    assert metadata.header == ["Attr Name", "Tag", "Description"]

def test_parse_table_reports_parsing_progress(docbook_sample_dom_1):  # noqa: F811
    """Test that parse_table reports parsing progress via the observer."""
    # Arrange

    from dcmspec.dom_table_spec_parser import DOMTableSpecParser
    from dcmspec.progress import ProgressStatus

    parser = DOMTableSpecParser()
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    events = []

    def observer(progress):
        events.append((progress.percent, progress.status))

    # Act

    parser.parse_table(
        dom=docbook_sample_dom_1,
        table_id="table_SAMPLE",
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        progress_observer=observer
    )

    # Assert

    # There are 2 data rows in docbook_sample_dom_1, so expect 2 progress events: 50% and 100%
    assert (50, ProgressStatus.PARSING_TABLE) in events
    assert (100, ProgressStatus.PARSING_TABLE) in events
    # Optionally, check that all events are for PARSING
    assert all(status == ProgressStatus.PARSING_TABLE for _, status in events)
