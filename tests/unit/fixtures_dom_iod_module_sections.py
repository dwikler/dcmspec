"""Fixtures providing a DocBook IOD + module + explanatory section, for IODSpecBuilder + ModuleSpecBuilder tests."""
import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def iod_with_module_and_section_dom():
    """Return a DOM with an IOD modules table referencing a module, whose attribute references a section.

    table_IOD's "Reference" cell is plain text "C.MODULE" (no anchor), matching how
    IODSpecBuilder._get_section_id_from_ref resolves it by default (unformatted=True strips
    the link, so the fallback plain-text branch is used) -- this is also how the real
    iodattributes CLI app configures its iod_factory (no unformatted override for the ref column).
    """
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
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
            <div class="section">
                <div class="table">
                    <a id="table_IOD" shape="rect"></a>
                    <p class="title"><strong>Table IOD. IOD Modules</strong></p>
                    <div class="table-contents">
                        <table frame="box" rules="all">
                            <thead>
                                <tr valign="top">
                                    <th align="center"><p>Module</p></th>
                                    <th align="center"><p>Reference</p></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr valign="top">
                                    <td align="left"><p>Sample Module</p></td>
                                    <td align="center"><p>C.MODULE</p></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="section">
                <div class="titlepage">
                    <div><div>
                        <h6 class="title"><a id="sect_C.MODULE" shape="rect"></a>C.MODULE Sample Module</h6>
                    </div></div>
                </div>
                <div class="table">
                    <a id="table_MODULE" shape="rect"></a>
                    <p class="title"><strong>Table MODULE. Sample Module Attributes</strong></p>
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
                <p><a id="para_1" shape="rect"></a>Explanatory text for the Frame Label attribute.</p>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")
