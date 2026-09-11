"""Fixtures providing DocBook section samples for tests."""
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
def docbook_sample_section_dom():
    """Return a BeautifulSoup DOM mimicking a DICOM DocBook explanatory section in CHTML.

    Contains a leaf section (sect_SAMPLE) with two paragraphs (one with an outgoing section
    reference and inline formatting), a note, an anchor-only empty paragraph, a figure, an
    informative table (preserved as-is, e.g. a Defined Terms table, not an attribute table),
    and a nested subsection (sect_SAMPLE.1) whose own content and references must not leak
    into sect_SAMPLE.
    """
    xhtml = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            {_VERSION_MARKUP}
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
                    <a id="para_1" shape="rect"></a>First paragraph of the <strong>sample</strong> section.</p>
                <p>
                    <a id="para_2" shape="rect"></a>See
                    <a class="xref" href="#sect_OTHER" title="C.7.6.16.2.2.5 Other Section" shape="rect">Section
                    C.7.6.16.2.2.5</a> for further explanation.</p>
                <div class="note" style="margin-left: 0.5in; margin-right: 0.5in;">
                    <h3 class="title">Note</h3>
                    <p>
                        <a id="para_note" shape="rect"></a>A caveat worth keeping.</p>
                </div>
                <p>
                    <a id="para_3" shape="rect"></a>
                </p>
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
                <div class="table">
                    <a id="table_SAMPLE" shape="rect"></a>
                    <p class="title"><strong>Table SAMPLE. Defined Terms</strong></p>
                    <div class="table-contents">
                        <table><tbody><tr>
                            <td>An informative table, preserved as part of the section.</td>
                        </tr></tbody></table>
                    </div>
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
                        <a id="para_4" shape="rect"></a>Content of the nested subsection, referencing
                        <a class="xref" href="#sect_SHOULD_NOT_LEAK" shape="rect">Section leak</a>, not included
                        when parsing sect_SAMPLE.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")


@pytest.fixture
def docbook_sample_section_with_variablelist_dom():
    """Return a BeautifulSoup DOM with a <div class="variablelist"> as a section's only content.

    Mimics a real DICOM "Defined Terms" glossary section (e.g. C.7.3.1.1.1 Modality), including
    a note nested inside one definition's own <dd>.
    """
    xhtml = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            {_VERSION_MARKUP}
            <div class="section">
                <div class="titlepage">
                    <div>
                        <div>
                            <h6 class="title">
                                <a id="sect_MODALITY" shape="rect"></a>C.7.3.1.1.1 Modality</h6>
                        </div>
                    </div>
                </div>
                <div class="variablelist">
                    <p class="title"><strong>Defined Terms:</strong></p>
                    <dl class="variablelist compact">
                        <dt><span class="term">CT</span></dt>
                        <dd><p><a id="para_1" shape="rect"></a>Computed Tomography</p></dd>
                        <dt><span class="term">PLAN</span></dt>
                        <dd>
                            <p><a id="para_2" shape="rect"></a>Plan</p>
                            <div class="note" style="margin-left: 0.5in;">
                                <h3 class="title">Note</h3>
                                <p>
                                    <a id="para_3" shape="rect"></a>The term "PLAN" denotes planned activities.</p>
                            </div>
                        </dd>
                    </dl>
                </div>
            </div>
        </body>
    </html>
    """
    return BeautifulSoup(xhtml, "lxml-xml")


@pytest.fixture
def docbook_grouping_section_dom():
    """Return a BeautifulSoup DOM mimicking a "grouping" section with no content of its own.

    Mirrors a real DICOM "<Module> Attribute Descriptions" section (e.g. C.7.6.4b.1 Enhanced
    Contrast/Bolus Module Attribute Descriptions): sect_GROUP has no direct content besides its
    own heading, only two subsections. sect_GROUP.1 has real content (a paragraph with an
    outgoing reference and an image). sect_GROUP.2 is itself a further grouping section with no
    content of its own, delegating one level deeper to sect_GROUP.2.1 -- exercising recursive
    delegation through more than one empty container.
    """
    xhtml = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            {_VERSION_MARKUP}
            <div class="section">
                <div class="titlepage">
                    <div>
                        <div>
                            <h6 class="title">
                                <a id="sect_GROUP" shape="rect"></a>C.9 Sample Attribute Descriptions</h6>
                        </div>
                    </div>
                </div>
                <div class="section">
                    <div class="titlepage">
                        <div>
                            <div>
                                <h6 class="title">
                                    <a id="sect_GROUP.1" shape="rect"></a>C.9.1 First Attribute</h6>
                            </div>
                        </div>
                    </div>
                    <p>
                        <a id="para_1" shape="rect"></a>Explanation of the first attribute, see
                        <a class="xref" href="#sect_OTHER" shape="rect">Section C.7.6.16.2.2.5</a>.</p>
                    <div class="figure">
                        <a id="figure_GROUP.1-1" shape="rect"></a>
                        <div class="figure-contents">
                            <div class="mediaobject">
                                <img src="figures/PS3.3_GROUP.1-1.svg" alt="First Attribute Figure" />
                            </div>
                        </div>
                        <p class="title"><strong>Figure GROUP.1-1. First Attribute Figure</strong></p>
                    </div>
                </div>
                <div class="section">
                    <div class="titlepage">
                        <div>
                            <div>
                                <h6 class="title">
                                    <a id="sect_GROUP.2" shape="rect"></a>C.9.2 Second Attribute</h6>
                            </div>
                        </div>
                    </div>
                    <div class="section">
                        <div class="titlepage">
                            <div>
                                <div>
                                    <h6 class="title">
                                        <a id="sect_GROUP.2.1" shape="rect"></a>C.9.2.1 Second Attribute Detail</h6>
                                </div>
                            </div>
                        </div>
                        <p>
                            <a id="para_2" shape="rect"></a>Explanation nested two levels below sect_GROUP.</p>
                    </div>
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
