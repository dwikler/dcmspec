"""Tests for the PDFDocHandler class in dcmspec.pdf_doc_handler."""
import pytest
from unittest.mock import MagicMock
import logging

from dcmspec.config import Config
from dcmspec.pdf_doc_handler import PDFDocHandler


def make_handler():
    """Test helper to create a PDFDocHandler with a real Config and a test logger."""
    return PDFDocHandler(config=Config(), logger=logging.getLogger("test"))

def test_load_document_happy_path(monkeypatch, patch_dirs):
    """Test load_document returns expected result when all arguments are provided and file exists."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    pad_columns = 2
    table_id = "T-1"
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    dummy_tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]}
    ]
    dummy_concat = {"header": ["A", "B"], "data": [["C", "D"]], "table_id": table_id}

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "extract_tables", lambda pdf, pn: dummy_tables)
    monkeypatch.setattr(handler, "concat_tables", lambda tables, ti, table_id=None, pad_columns=None: dummy_concat)

    # Act
    result = handler.load_document(
        cache_file_name=cache_file_name,
        url=url,
        force_download=False,
        page_numbers=page_numbers,
        table_indices=table_indices,
        pad_columns=pad_columns,
        table_id=table_id,
    )

    # Assert
    assert result == dummy_concat

def test_load_document_download(monkeypatch, patch_dirs):
    """Test load_document triggers download if file does not exist."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    monkeypatch.setattr("os.path.exists", lambda path: False)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: "test.pdf")
    monkeypatch.setattr(handler, "extract_tables", lambda pdf, pn: [])
    monkeypatch.setattr(handler, "concat_tables", lambda tables, ti, table_id=None, pad_columns=None: {})

    # Act
    handler.load_document(
        cache_file_name=cache_file_name,
        url=url,
        force_download=False,
        page_numbers=page_numbers,
        table_indices=table_indices,
    )

def test_load_document_missing_url(monkeypatch, patch_dirs):
    """Test load_document raises ValueError if url is missing and download is needed."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    monkeypatch.setattr("os.path.exists", lambda path: False)

    # Act & Assert
    with pytest.raises(ValueError, match="URL must be provided to download the file."):
        handler.load_document(
            cache_file_name=cache_file_name,
            url=None,
            force_download=True,
            page_numbers=page_numbers,
            table_indices=table_indices,
        )

def test_load_document_missing_args(monkeypatch, patch_dirs):
    """Test load_document raises ValueError if page_numbers or table_indices are missing."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "extract_tables", lambda pdf, pn: [])
    monkeypatch.setattr(handler, "concat_tables", lambda tables, ti, table_id=None, pad_columns=None: {})

    # Act & Assert
    with pytest.raises(ValueError, match="page_numbers and table_indices must be provided"):
        handler.load_document(
            cache_file_name=cache_file_name,
            url=url,
            force_download=False,
            page_numbers=None,
            table_indices=None,
        )

def test_download_calls_super(monkeypatch, patch_dirs):
    """Test download calls the super().download method with correct arguments."""
    # Arrange
    handler = make_handler()
    called = {}
    def fake_super_download(url, file_path, binary):
        called["args"] = (url, file_path, binary)
        return "SAVED_PATH"
    monkeypatch.setattr("dcmspec.doc_handler.DocHandler.download", staticmethod(fake_super_download))
    url = "http://example.com/file.pdf"
    cache_file_name = "test.pdf"
    expected_path = str(patch_dirs / "cache" / "standard" / "test.pdf")

    # Act
    result = handler.download(url, cache_file_name)

    # Assert
    assert result == "SAVED_PATH"
    assert called["args"] == (url, expected_path, True)

def test_extract_tables_happy(monkeypatch, patch_dirs):
    """Test extract_tables returns expected structure for multiple pages with tables."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page, dummy_page]
    dummy_page.extract_tables.side_effect = [
        [[["A", "B"], ["C", "D"]]],
        [[["E", "F"], ["G", "H"]]]
    ]
    # Act
    result = handler.extract_tables(dummy_pdf, [1, 2])
    # Assert
    assert isinstance(result, list)
    assert result[0]["header"] == ["A", "B"]
    assert result[0]["data"] == [["C", "D"]]
    assert result[1]["header"] == ["E", "F"]
    assert result[1]["data"] == [["G", "H"]]
    assert result[0]["page"] == 1
    assert result[1]["page"] == 2

def test_extract_tables_empty(monkeypatch, patch_dirs):
    """Test extract_tables returns empty list if no tables are found."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]
    dummy_page.extract_tables.return_value = []
    # Act
    result = handler.extract_tables(dummy_pdf, [1])
    # Assert
    assert result == []

def test_extract_tables_page_num_out_of_range(monkeypatch, patch_dirs):
    """Test extract_tables raises IndexError if page number is out of range."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]  # Only 1 page
    # Act & Assert
    with pytest.raises(IndexError, match="Page number 2 is out of range for this PDF"):
        handler.extract_tables(dummy_pdf, [2])

def test_concat_tables_basic(monkeypatch, patch_dirs):
    """Test concat_tables concatenates tables with matching headers."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]},
        {"page": 2, "index": 0, "header": ["A", "B"], "data": [["E", "F"]]}
    ]
    table_indices = [(1, 0), (2, 0)]
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    assert result["data"] == [["C", "D"], ["E", "F"]]

def test_concat_tables_pads_and_truncates_to_header(monkeypatch, patch_dirs):
    """Test concat_tables pads or truncates rows to match header length."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C"], ["D", "E", "F"]]},
    ]
    table_indices = [(1, 0)]
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    # First row is padded, second row is truncated
    assert result["data"] == [["C", ""], ["D", "E"]]

def test_concat_tables_header_mismatch(monkeypatch, caplog, patch_dirs):
    """Test concat_tables logs a warning if headers do not match."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]},
        {"page": 2, "index": 0, "header": ["X", "Y"], "data": [["E", "F"]]}
    ]
    table_indices = [(1, 0), (2, 0)]
    caplog.set_level(logging.WARNING)
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    assert result["data"] == [["C", "D"], ["E", "F"]]
    assert "Header mismatch" in caplog.text

def test_extract_notes_basic(monkeypatch, patch_dirs):
    """Test extract_notes extracts notes from PDF text."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_page.extract_text.return_value = "Note 1: This is a note.\nSome more text\nNote 2: Second note."
    dummy_pdf.pages = [dummy_page]
    # Act
    result = handler.extract_notes(dummy_pdf, [1])
    # Assert
    assert "Note 1:" in result
    assert "Note 2:" in result
    assert result["Note 1:"]["text"].startswith("This is a note.")
    assert result["Note 2:"]["text"].startswith("Second note.")

def test_extract_notes_with_table_id(monkeypatch, patch_dirs):
    """Test extract_notes includes table_id in the result if provided."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_page.extract_text.return_value = "Note 1: Text"
    dummy_pdf.pages = [dummy_page]
    # Act
    result = handler.extract_notes(dummy_pdf, [1], table_id="T-1")
    # Assert
    assert "Note 1:" in result
    assert result["Note 1:"]["table_id"] == "T-1"

def test_extract_notes_multi_page(monkeypatch, patch_dirs):
    """Test extract_notes can extract notes spanning multiple pages."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page1 = MagicMock()
    dummy_page2 = MagicMock()
    # Note starts on page 1 and continues on page 2
    dummy_page1.extract_text.return_value = "Header\nNote 1: This is a note that starts on page 1"
    dummy_page2.extract_text.return_value = "and continues on page 2. Footer"
    dummy_pdf.pages = [dummy_page1, dummy_page2]

    # Act
    result = handler.extract_notes(dummy_pdf, [1, 2])

    # Assert
    # The note should be concatenated across both pages
    assert "Note 1:" in result
    assert "This is a note that starts on page 1 and continues on page 2." in result["Note 1:"]["text"]

def test_extract_notes_interrupted_by_headers_footers(monkeypatch, patch_dirs):
    """Test extract_notes handles notes interrupted by headers, footers, or end patterns."""
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page1 = MagicMock()
    dummy_page2 = MagicMock()
    # Note starts on page 1, continues on page 2, both have headers/footers as separate lines
    dummy_page1.extract_text.return_value = "Header\nNote 2: This note is interrupted by a header."
    dummy_page2.extract_text.return_value = "Header\nStill part of note 2.\nFooter\nEnd of Notes"
    dummy_pdf.pages = [dummy_page1, dummy_page2]

    # Act
    result = handler.extract_notes(
        dummy_pdf,
        [1, 2],
        header_footer_pattern=r"^(Header|Footer|End of Notes)$"
    )

    # Assert
    # The note should be correctly concatenated and not include headers/footers
    assert "Note 2:" in result
    assert "This note is interrupted by a header. Still part of note 2." in result["Note 2:"]["text"]
    assert "Header" not in result["Note 2:"]["text"]
    assert "Footer" not in result["Note 2:"]["text"]
    assert "End of Notes" not in result["Note 2:"]["text"]

