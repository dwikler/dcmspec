"""Tests for the DOMUtils class in dcmspec.dom_utils."""
from bs4 import BeautifulSoup
from dcmspec.dom_utils import DOMUtils

# Import sample DOM with tables fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_tables import (
    docbook_sample_dom_1,  # noqa: F401
    section_dom,  # noqa: F401
)

def test_get_table_finds_table(docbook_sample_dom_1):  # noqa: F811
    """Test DOMUtils.get_table returns the table element when the anchor and table exist."""
    dom_utils = DOMUtils()
    table = dom_utils.get_table(docbook_sample_dom_1, "table_SAMPLE")
    assert table is not None
    assert table.name == "table"

def test_get_table_anchor_not_found(docbook_sample_dom_1, caplog):  # noqa: F811
    """Test DOMUtils.get_table returns None and logs a warning if the anchor is not found."""
    dom_utils = DOMUtils()
    with caplog.at_level("WARNING"):
        table = dom_utils.get_table(docbook_sample_dom_1, "table_NOT_FOUND")
    assert table is None
    assert "Table Id table_NOT_FOUND not found." in caplog.text

def test_get_table_table_not_found(docbook_sample_dom_1, caplog):  # noqa: F811
    """Test DOMUtils.get_table returns None and logs a warning if the table is not found after the anchor."""
    # Remove the table after the anchor to simulate missing table
    dom = docbook_sample_dom_1
    anchor = dom.find("a", {"id": "table_SAMPLE"})
    next_table = anchor.find_next("table")
    next_table.decompose()
    dom_utils = DOMUtils()
    with caplog.at_level("WARNING"):
        table = dom_utils.get_table(dom, "table_SAMPLE")
    assert table is None
    assert "Table table_SAMPLE not found." in caplog.text

def test_get_table_id_from_section(section_dom):  # noqa: F811
    """Test DOMUtils.get_table_id_from_section returns the correct table id for a section anchor."""
    dom_utils = DOMUtils()
    section_anchor = "sect_C.7.1.1"
    table_id = dom_utils.get_table_id_from_section(section_dom, section_anchor)
    assert table_id == "table_C.7-1"

def test_get_table_id_from_section_not_found(section_dom, caplog):  # noqa: F811
    """Test DOMUtils.get_table_id_from_section returns None if the section anchor is not found and logs a warning."""
    dom_utils = DOMUtils()
    section_anchor = "sect_DOES_NOT_EXIST"
    with caplog.at_level("WARNING"):
        table_id = dom_utils.get_table_id_from_section(section_dom, section_anchor)
    assert table_id is None
    assert "Section with id 'sect_DOES_NOT_EXIST' not found." in caplog.text

def test_get_table_id_from_section_no_parent_section(caplog):
    """Test DOMUtils.get_table_id_from_section returns None if the anchor is not inside a section div."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div>
                <a id="sect_XYZ"></a>
                <div class="table">
                    <a id="table_XYZ"></a>
                </div>
            </div>
        </body>
    </html>
    """
    dom = BeautifulSoup(xhtml, "lxml-xml")
    dom_utils = DOMUtils()
    with caplog.at_level("WARNING"):
        table_id = dom_utils.get_table_id_from_section(dom, "sect_XYZ")
    assert table_id is None
    assert "No parent <div class='section'> found for section id 'sect_XYZ'." in caplog.text

def test_get_table_id_from_section_no_table_in_section(caplog):
    """Test DOMUtils.get_table_id_from_section returns None if there is no table div in the section."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <a id="sect_XYZ"></a>
                <p>No table here.</p>
            </div>
        </body>
    </html>
    """
    dom = BeautifulSoup(xhtml, "lxml-xml")
    dom_utils = DOMUtils()
    with caplog.at_level("WARNING"):
        table_id = dom_utils.get_table_id_from_section(dom, "sect_XYZ")
    assert table_id is None
    assert "No <div class='table'> found in section for section id 'sect_XYZ'." in caplog.text

def test_get_table_id_from_section_no_table_anchor(caplog):
    """Test DOMUtils.get_table_id_from_section returns None if there is no anchor with id in the table div."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <a id="sect_XYZ"></a>
                <div class="table">
                    <p>No anchor here.</p>
                </div>
            </div>
        </body>
    </html>
    """
    dom = BeautifulSoup(xhtml, "lxml-xml")
    dom_utils = DOMUtils()
    with caplog.at_level("WARNING"):
        table_id = dom_utils.get_table_id_from_section(dom, "sect_XYZ")
    assert table_id is None
    assert "No table id found in <div class='table'> for section id 'sect_XYZ'." in caplog.text
