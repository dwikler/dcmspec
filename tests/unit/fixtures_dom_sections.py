"""Fixtures providing DocBook section samples for tests."""
import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def docbook_sample_section_dom():
    """Return a BeautifulSoup DOM mimicking a DICOM DocBook explanatory section in CHTML.

    Contains a leaf section (sect_SAMPLE) with two paragraphs (one with an outgoing
    section reference), a figure, and a nested subsection (sect_SAMPLE.1) that should
    not be included when parsing sect_SAMPLE itself.
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
                <div class="titlepage">
                    <div>
                        <div>
                            <h6 class="title">
                                <a id="sect_SAMPLE" shape="rect"></a>C.7.6.16.2.2.1 Sample Section</h6>
                        </div>
                    </div>
                </div>
                <p>
                    <a id="para_1" shape="rect"></a>First paragraph of the sample section.</p>
                <p>
                    <a id="para_2" shape="rect"></a>See
                    <a class="xref" href="#sect_OTHER" title="C.7.6.16.2.2.5 Other Section" shape="rect">Section
                    C.7.6.16.2.2.5</a> for further explanation.</p>
                <div class="figure">
                    <a id="figure_SAMPLE-1" shape="rect"></a>
                    <div class="figure-contents">
                        <div class="mediaobject">
                            <img src="figures/PS3.3_SAMPLE-1.svg" alt="Sample Figure" />
                        </div>
                    </div>
                    <p class="title">
                        <strong>Figure SAMPLE-1. Sample Figure</strong>
                    </p>
                </div>
                <div class="section">
                    <div class="titlepage">
                        <div>
                            <div>
                                <h6 class="title">
                                    <a id="sect_SAMPLE.1" shape="rect"></a>C.7.6.16.2.2.1.1 Sample Subsection</h6>
                            </div>
                        </div>
                    </div>
                    <p>
                        <a id="para_3" shape="rect"></a>Content of the nested subsection, not included when
                        parsing sect_SAMPLE.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")


@pytest.fixture
def docbook_sample_section_missing_heading_dom():
    """Return a BeautifulSoup DOM with a section anchor that has no enclosing heading tag."""
    xhtml = """
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <div class="section">
                <a id="sect_NO_HEADING" shape="rect"></a>
                <p><a id="para_1" shape="rect"></a>Orphan paragraph, no heading above it.</p>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")
