"""Fixtures providing DocBook samples for tests."""
import pytest
from bs4 import BeautifulSoup

@pytest.fixture
def docbook_sample_dom_1():
    """Return a BeautifulSoup DOM mimicking DICOM DocBook in CHTML, with a name to test _sanitize_string."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <table width="100%">
                <tbody>
                    <tr>
                        <th colspan="1" align="center" rowspan="1">
                            <span class="documentreleaseinformation">DICOM PS3.3 2025b - Information Object Definitions</span>
                        </th>
                    </tr>
                </tbody>
            </table>
            <div class="section">
            <div class="titlepage">
                <h4 class="title">
                <a id="sect_SAMPLE" shape="rect"></a>Sample Section
                </h4>
            </div>
            <div class="table">
                <a id="table_SAMPLE" shape="rect"></a>
                <p class="title"><strong>Table SAMPLE. Sample Attributes</strong></p>
                <div class="table-contents">
                <table frame="box" rules="all">
                    <thead>
                    <tr valign="top">
                        <th align="center"><p>Attr Name</p></th>
                        <th align="center"><p>Tag</p></th>
                        <th align="center"><p>Type</p></th>
                        <th align="center"><p>Description</p></th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr valign="top">
                        <td align="left"><p>Attr Name (Tést)</p></td>
                        <td align="center"><p>(0101,0001)</p></td>
                        <td align="center"><p>1</p></td>
                        <td align="left"><p>Desc1</p></td>
                    </tr>
                    <tr valign="top">
                        <td align="left"><p>AttrName2</p></td>
                        <td align="center"><p>(0101,0002)</p></td>
                        <td align="center"><p>2</p></td>
                        <td align="left"><p>Desc2</p></td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")


@pytest.fixture
def docbook_sample_dom_2():
    """Return a BeautifulSoup DOM mimicking DICOM DocBook in HTML."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="titlepage">
                <div>
                    <div font-size="14pt">
                        <h1 class="title">
                            <a id="PS3.3" shape="rect"></a>PS3.3</h1>
                    </div>
                    <div font-size="14pt">
                        <h2 class="subtitle">DICOM PS3.3 2025b - Information Object Definitions</h2>
                    </div>
                </div>
            </div>
            <div class="section">
            <div class="titlepage">
                <h4 class="title">
                <a id="sect_SAMPLE" shape="rect"></a>Sample Section
                </h4>
            </div>
            <div class="table">
                <a id="table_SAMPLE" shape="rect"></a>
                <p class="title"><strong>Table SAMPLE. Sample Attributes</strong></p>
                <div class="table-contents">
                <table frame="box" rules="all">
                    <thead>
                    <tr valign="top">
                        <th align="center"><p>Attr Name</p></th>
                        <th align="center"><p>Tag</p></th>
                        <th align="center"><p>Type</p></th>
                        <th align="center"><p>Description</p></th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr valign="top">
                        <td align="left"><p>AttrName1</p></td>
                        <td align="center"><p>(0101,0001)</p></td>
                        <td align="center"><p>1</p></td>
                        <td align="left"><p>Desc1</p></td>
                    </tr>
                    <tr valign="top">
                        <td align="left"><p>AttrName2</p></td>
                        <td align="center"><p>(0101,0002)</p></td>
                        <td align="center"><p>2</p></td>
                        <td align="left"><p>Desc2</p></td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_empty_rows_and_cells_dom():
    """Return a DOM with empty rows and empty cells."""
    xhtml = """
    <html>
        <body>
            <div class="table">
                <a id="table_EMPTY" shape="rect"></a>
                <div class="table-contents">
                    <table>
                        <thead>
                            <tr>
                                <th>Col1</th>
                                <th>Col2</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr></tr>
                            <tr>
                                <td></td>
                                <td>Value2</td>
                            </tr>
                            <tr>
                                <td>Value3</td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
    </html>
    """
    from bs4 import BeautifulSoup
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_colspan_dom():
    """Return a DocBook-style XHTML DOM with a table that uses colspan."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <div class="table">
                    <a id="table_COLSPAN" shape="rect"></a>
                    <p class="title"><strong>Table COLSPAN. Colspan Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Col1</p></th>
                                    <th align="center"><p>Col2</p></th>
                                    <th align="center"><p>Col3</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td colspan="2"><p>A</p></td>
                                    <td><p>B</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_mixed_colspan_dom():
    """Return a DocBook-style XHTML DOM with a table where some rows have a missing column (colspan) and others do not."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <div class="table">
                    <a id="table_MIXED" shape="rect"></a>
                    <p class="title"><strong>Table MIXED. Mixed Colspan Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Col1</p></th>
                                    <th align="center"><p>Col2</p></th>
                                    <th align="center"><p>Col3</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td colspan="2"><p>A</p></td>
                                    <td><p>B</p></td>
                                </tr>
                                <tr valign="top">
                                    <td><p>C</p></td>
                                    <td><p>D</p></td>
                                    <td><p>E</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_rowspan_dom():
    """Return a DocBook-style XHTML DOM with a table that uses rowspan."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <div class="table">
                    <a id="table_ROWSPAN" shape="rect"></a>
                    <p class="title"><strong>Table ROWSPAN. Rowspan Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Col1</p></th>
                                    <th align="center"><p>Col2</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td rowspan="2"><p>A</p></td>
                                    <td><p>B</p></td>
                                </tr>
                                <tr valign="top">
                                    <td><p>C</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_colspan_rowspan_dom():
    """Return a DocBook-style XHTML DOM with a table that uses both colspan and rowspan."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <div class="table">
                    <a id="table_COLSPANROWSPAN" shape="rect"></a>
                    <p class="title"><strong>Table COLSPANROWSPAN. Colspan+Rowspan Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Col1</p></th>
                                    <th align="center"><p>Col2</p></th>
                                    <th align="center"><p>Col3</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td rowspan="2" colspan="2"><p>A</p></td>
                                    <td><p>B</p></td>
                                </tr>
                                <tr valign="top">
                                    <td><p>C</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def table_include_dom():
    """Return a BeautifulSoup DOM mimicking DocBook XHTML with an include row and a macro table."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <div class="table">
                    <a id="table_MAIN" shape="rect"></a>
                    <p class="title"><strong>Table MAIN. Main Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Col1</p></th>
                                    <th align="center"><p>Col2</p></th>
                                    <th align="center"><p>Col3</p></th>
                                    <th align="center"><p>Col4</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td align="left"><p>AttrName1</p></td>
                                    <td align="center"><p>(0101,0001)</p></td>
                                    <td align="center"><p>1</p></td>
                                    <td align="left"><p>Desc1</p></td>
                                </tr>
                                <tr valign="top">
                                    <td align="left"><p>AttrName2</p></td>
                                    <td align="center"><p>(0101,0002)</p></td>
                                    <td align="center"><p>2</p></td>
                                    <td align="left"><p>Desc2</p></td>
                                </tr>
                                <tr valign="top">
                                    <td align="left" colspan="4" rowspan="1">
                                        <p>
                                            <span class="italic">Include <a class="xref" href="#table_MACRO">Table Macro</a></span>
                                        </p>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="table">
                    <a id="table_MACRO" shape="rect"></a>
                    <p class="title"><strong>Table MACRO. Macro Table</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Attr Name</p></th>
                                    <th align="center"><p>Tag</p></th>
                                    <th align="center"><p>Type</p></th>
                                    <th align="center"><p>Description</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td align="left"><p>AttrName10</p></td>
                                    <td align="center"><p>(0101,0010)</p></td>
                                    <td align="center"><p>3</p></td>
                                    <td align="left"><p>Bla</p></td>
                                </tr>
                                <tr valign="top">
                                    <td align="left"><p>AttrName11</p></td>
                                    <td align="center"><p>(0101,0011)</p></td>
                                    <td align="center"><p>3</p></td>
                                    <td align="left"><p>Bla</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")

@pytest.fixture
def section_dom():
    """Return a BeautifulSoup DOM with a section and a table for get_table_id_from_section tests."""
    xhtml = """
    <div class="section">
        <div class="titlepage">
            <div>
                <div>
                    <h4 class="title">
                        <a id="sect_C.7.1.1" shape="rect"></a>C.7.1.1&nbsp;Patient Module</h4>
                </div>
            </div>
        </div>
        <p>
            <a class="xref" href="#table_C.7-1" title="Table&nbsp;C.7-1.&nbsp;Patient Module Attributes" shape="rect">Table&nbsp;C.7-1</a>
        </p>
        <div class="table">
            <a id="table_C.7-1" shape="rect"></a>
            <p class="title">
                <strong>Table&nbsp;C.7-1.&nbsp;Patient Module Attributes</strong>
            </p>
            <div class="table-contents">
                <table frame="box" rules="all">
                    <thead>
                        <tr>
                            <th>Attribute Name</th>
                            <th>Tag</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Patient's Name</td>
                            <td>(0010,0010)</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return BeautifulSoup(xhtml, "lxml-xml")