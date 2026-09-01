"""Fixtures providing a DocBook module table plus explanatory sections, for ModuleSpecBuilder tests."""
import pytest
from bs4 import BeautifulSoup

_VERSION_MARKUP = """
    <table width="100%">
        <tbody>
            <tr>
                <th colspan="1" align="center" rowspan="1">
                    <span class="documentreleaseinformation">
                        DICOM PS3.3 2025b - Information Object Definitions
                    </span>
                </th>
            </tr>
        </tbody>
    </table>
"""


@pytest.fixture
def module_with_sections_dom():
    """Return a DOM with a module table referencing sect_C.1, which itself references sect_C.2.

    sect_C.1 also has a figure, to exercise image resolution. The module's second row has no
    section reference, to confirm it triggers no resolution.
    """
    xhtml = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            {_VERSION_MARKUP}
            <div class="section">
                <div class="table">
                    <a id="table_MODULE" shape="rect"></a>
                    <p class="title"><strong>Table MODULE. Module Attributes</strong></p>
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
                                    <td align="left"><p>Frame Label</p></td>
                                    <td align="center"><p>(0020,9453)</p></td>
                                    <td align="center"><p>3</p></td>
                                    <td align="left">
                                        <p>See
                                            <a class="xref" href="#sect_C.1" title="C.1 First Section"
                                               shape="rect">Section C.1</a>
                                            for further explanation.</p>
                                    </td>
                                </tr>
                                <tr valign="top">
                                    <td align="left"><p>Other Attr</p></td>
                                    <td align="center"><p>(0020,9999)</p></td>
                                    <td align="center"><p>3</p></td>
                                    <td align="left"><p>No refs here.</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="section">
                <div class="titlepage">
                    <div><div>
                        <h6 class="title"><a id="sect_C.1" shape="rect"></a>C.1 First Section</h6>
                    </div></div>
                </div>
                <p>
                    <a id="para_1" shape="rect"></a>First section text, referencing
                    <a class="xref" href="#sect_C.2" title="C.2 Second Section" shape="rect">Section C.2</a>.</p>
                <div class="figure">
                    <a id="figure_C.1-1" shape="rect"></a>
                    <div class="figure-contents">
                        <div class="mediaobject">
                            <img src="figures/PS3.3_C.1-1.svg" alt="Sample Figure" />
                        </div>
                    </div>
                    <p class="title"><strong>Figure C.1-1. Sample Figure</strong></p>
                </div>
            </div>
            <div class="section">
                <div class="titlepage">
                    <div><div>
                        <h6 class="title"><a id="sect_C.2" shape="rect"></a>C.2 Second Section</h6>
                    </div></div>
                </div>
                <p><a id="para_2" shape="rect"></a>Second section text, no further refs.</p>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")


@pytest.fixture
def module_with_circular_sections_dom():
    """Return a DOM with a module table referencing sect_LOOP1, which references sect_LOOP2 and back."""
    xhtml = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            {_VERSION_MARKUP}
            <div class="section">
                <div class="table">
                    <a id="table_MODULE" shape="rect"></a>
                    <p class="title"><strong>Table MODULE. Module Attributes</strong></p>
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
                                    <td align="left"><p>Looping Attr</p></td>
                                    <td align="center"><p>(0020,9453)</p></td>
                                    <td align="center"><p>3</p></td>
                                    <td align="left">
                                        <p>See
                                            <a class="xref" href="#sect_LOOP1" title="Loop 1"
                                               shape="rect">Section LOOP1</a>.</p>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="section">
                <div class="titlepage">
                    <div><div>
                        <h6 class="title"><a id="sect_LOOP1" shape="rect"></a>Loop 1</h6>
                    </div></div>
                </div>
                <p>
                    <a id="para_1" shape="rect"></a>Refers to
                    <a class="xref" href="#sect_LOOP2" title="Loop 2" shape="rect">Section LOOP2</a>.</p>
            </div>
            <div class="section">
                <div class="titlepage">
                    <div><div>
                        <h6 class="title"><a id="sect_LOOP2" shape="rect"></a>Loop 2</h6>
                    </div></div>
                </div>
                <p>
                    <a id="para_2" shape="rect"></a>Refers back to
                    <a class="xref" href="#sect_LOOP1" title="Loop 1" shape="rect">Section LOOP1</a>.</p>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")
