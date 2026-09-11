"""Tests for the UPSXHTMLDocHandler class in dcmspec.ups_xhtml_doc_handler."""
import pytest
from bs4 import BeautifulSoup
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler

@pytest.fixture
def ups_dom_with_include_row():
    """Return a BeautifulSoup DOM with the exact copy of the Output Information Sequence and Include row structure."""
    xhtml = """
    <html>
        <body>
            <div class="table">
                <a id="table_CC.2.5-3"></a>
                <table>
                    <tr valign="top">
                        <td align="left" rowspan="1" colspan="1">
                            <p>
                                <a id="para_52418082-3d7d-4a50-a91f-819718666a61" shape="rect"></a>&gt;Output Information Sequence</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_96b98b49-b2e8-48a6-aa8d-fa0e9bf54787" shape="rect"></a>(0040,4033)</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_be50f156-c615-4fe2-8be4-182a0ee4d671" shape="rect"></a>Not Allowed</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_b2be313e-aa05-469e-85a1-0a0805c811e9" shape="rect"></a>2/2</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_92722ac4-1c66-4d71-bf07-39819c7d82be" shape="rect"></a>P</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_dcd17719-7458-430c-9ed5-0a39545c472b" shape="rect"></a>-/2</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_1612d08f-0e7f-435c-870d-76da009705f9" shape="rect"></a>-</p>
                        </td>
                        <td align="center" rowspan="1" colspan="1">
                            <p>
                                <a id="para_d6805ea4-401f-40c2-9469-10835e2ee48e" shape="rect"></a>-</p>
                        </td>
                        <td align="left" rowspan="1" colspan="1">
                            <p>
                                <a id="para_1350edb9-f8e1-432a-8843-e44ed575b932" shape="rect"></a>If there are no relevant output objects, then this sequence may have no items.</p>
                        </td>
                    </tr>
                    <tr valign="top">
                        <td align="left" colspan="9" rowspan="1">
                            <p>
                                <a id="para_9e74be16-66a8-44dc-b20b-491b62008e92" shape="rect"></a>
                                <span class="italic">&gt;Include <a class="xref" id="include_row" href="#table_CC.2.5-2c" title="Table&nbsp;CC.2.5-2c.&nbsp;Referenced Instances and Access Macro" shape="rect">Table&nbsp;CC.2.5-2c “Referenced Instances and Access Macro”</a>
                                </span>
                            </p>
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

def test_patch_table_adds_extra_gt(ups_dom_with_include_row):
    """Test that _patch_table adds an extra '>' to the Include row under Output Information Sequence."""
    handler = UPSXHTMLDocHandler()
    dom = ups_dom_with_include_row
    handler._patch_table(dom, "table_CC.2.5-3")
    # Find the patched span
    span = dom.find("span", class_="italic")
    assert span is not None
    # The text should now start with '>>Include'
    assert ">>Include" in span.text

def test_patch_table_warns_if_no_target(caplog):
    """Test that _patch_table logs a warning if the Output Information Sequence Include row is not found."""
    handler = UPSXHTMLDocHandler()
    # DOM without the target element
    xhtml = """
    <html>
        <body>
            <table id="table_CC.2.5-3">
                <tr>
                    <td>Some Other Sequence</td>
                </tr>
            </table>
        </body>
    </html>
    """
    dom = BeautifulSoup(xhtml, "lxml-xml")
    with caplog.at_level("WARNING"):
        handler._patch_table(dom, "table_CC.2.5-3")
    assert "Output Information Sequence Include Row element ID not found" in caplog.text

def test_search_element_id_finds_include_row(ups_dom_with_include_row):
    """Test that _search_element_id finds the correct include row id."""
    handler = UPSXHTMLDocHandler()
    dom = ups_dom_with_include_row
    include_id = handler._search_element_id(dom, "table_CC.2.5-3", ">Output Information Sequence")
    assert include_id == "para_9e74be16-66a8-44dc-b20b-491b62008e92"

def test_search_element_id_returns_none_if_not_found():
    """Test that _search_element_id returns None if the sequence label is not found."""
    handler = UPSXHTMLDocHandler()
    xhtml = """
    <html>
        <body>
            <table id="table_CC.2.5-3">
                <tr>
                    <td>Other Sequence</td>
                </tr>
            </table>
        </body>
    </html>
    """
    dom = BeautifulSoup(xhtml, "lxml-xml")
    include_id = handler._search_element_id(dom, "table_CC.2.5-3", ">Output Information Sequence")
    assert include_id is None

    