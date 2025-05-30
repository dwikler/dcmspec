"""Tests for the XHTMLDocHandler class in dcmspec.xhtml_doc_handler."""
from bs4 import ParserRejectedMarkup
from unittest.mock import patch
import os
import pytest
from requests.exceptions import RequestException
from dcmspec.xhtml_doc_handler import XHTMLDocHandler

class DummyResponseSuccess:
    """A dummy HTTP response object that simulates a successful requests.get call."""

    def __init__(self):
        """Initialize a successful dummy response."""
        self.text = "A\u200bB\u00a0C"
        self.status_code = 200
        self.encoding = None
    def raise_for_status(self):
        """Simulate a successful status check (do nothing)."""
        pass
        
class DummyResponseFailure:
    """A dummy HTTP response object that simulates a failed requests.get call."""

    def raise_for_status(self): 
        """Simulate a failed request by raising an exception."""
        raise RequestException("fail")

def _standard_file_path(handler, file_name):
    """Return the standard file path for a given handler and file name."""
    cache_dir = handler.config.get_param("cache_dir")
    return os.path.join(cache_dir, "standard", file_name)

def test_download_success(monkeypatch, caplog):
    """Test that download calls helpers and logs info, and returns the correct file path."""
    handler = XHTMLDocHandler()
    file_name = "test.xhtml"
    file_path = _standard_file_path(handler, file_name)

    # Patch request get method
    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponseSuccess())

    # Call the download method
    result_path = handler.download("http://example.com", file_name)


    # Assert the file was created and contains the expected content
    assert result_path == file_path
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u200b" not in content
    assert "\u00a0" not in content
    assert "AB C" in content
    
    assert f"Downloading XHTML document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text


def test_download_failure_network(tmp_path, monkeypatch):
    """Test that download raises RuntimeError on network error."""
    handler = XHTMLDocHandler()
    handler.config.set_param("cache_dir", str(tmp_path))
    file_name = "test.xhtml"
    _standard_file_path(handler, file_name)

    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponseFailure())

    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_name)
    assert "Failed to download" in str(excinfo.value)

def test_download_failure_dir(monkeypatch):  # sourcery skip: simplify-generator
    """Test that download raises RuntimeError if directory creation fails."""
    handler = XHTMLDocHandler()
    file_name = "test.xhtml"

    # Patch os.makedirs to always raise OSError
    monkeypatch.setattr("os.makedirs", lambda *a, **k: (_ for _ in ()).throw(OSError("cannot create dir")))

    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_name)
    assert "Failed to create directory for" in str(excinfo.value)
    assert "cannot create dir" in str(excinfo.value)

def test_download_failure_save(monkeypatch):
    """Test that download raises RuntimeError if saving the file fails."""
    handler = XHTMLDocHandler()
    file_name = "test.xhtml"

    # Patch requests.get to return a successful dummy response
    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponseSuccess())

    # Patch builtins.open only for download call
    with patch("builtins.open", side_effect=OSError("save failed")):
        with pytest.raises(RuntimeError) as excinfo:
            handler.download("http://example.com", file_name)
    assert "Failed to save file" in str(excinfo.value)
    assert "save failed" in str(excinfo.value)

def test_parse_dom_success(tmp_path, caplog):
    """Test that parse_dom reads and parses a valid XHTML file, logs info, and returns a BeautifulSoup object."""
    handler = XHTMLDocHandler()
    file_path = _standard_file_path(handler, "file.xhtml")

    # Ensure the directory exists and write a simple XHTML file
    handler._ensure_dir_exists(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<root><tag>ok</tag></root>")

    with caplog.at_level("INFO"):
        dom = handler.parse_dom(file_path)

    assert dom.find("tag").text == "ok"
    assert f"Reading XHTML DOM from {file_path}" in caplog.text
    assert "XHTML DOM read successfully" in caplog.text

def test_parse_dom_file_read_error(tmp_path, caplog):
    """Test that parse_dom raises RuntimeError and logs error if file cannot be read."""
    handler = XHTMLDocHandler()
    file_path = _standard_file_path(handler, "nonexistent.xhtml")
    # Do not create the file

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.parse_dom(file_path)
    assert "Failed to read file" in str(excinfo.value)
    assert f"Failed to read file {file_path}" in caplog.text

def raise_bs4_parser_rejected_markup(*args, **kwargs):
    """Mock BeautifulSoup to always raise a bs4.ParserRejectedMarkup error."""
    raise ParserRejectedMarkup("Parser rejected markup.")

def test_parse_dom_parse_error(tmp_path, caplog, monkeypatch):
    """Test that parse_dom raises RuntimeError and logs error if file cannot be parsed."""
    handler = XHTMLDocHandler()
    file_path = _standard_file_path(handler, "bad.xhtml")

    handler._ensure_dir_exists(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<root><tag>unclosed</root>")  # Malformed XML

    # Patch the BeautifulSoup used in the xhtml_doc_handler module
    monkeypatch.setattr("dcmspec.xhtml_doc_handler.BeautifulSoup", raise_bs4_parser_rejected_markup)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.parse_dom(file_path)
    assert "Failed to parse XHTML file" in str(excinfo.value)
    assert f"Failed to parse XHTML file {file_path}" in caplog.text

def test_get_dom_force_download(monkeypatch):
    """Test that get_dom downloads and parses when force_download is True."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    result = handler.get_dom(file_name, url="http://example.com", force_download=True)
    assert result == "DOM_OBJECT"
    assert call_log == ["download", "parse_dom"]

def test_get_dom_file_missing(monkeypatch):
    """Test that get_dom downloads and parses when file does not exist and force_download is False."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    result = handler.get_dom(file_name, url="http://example.com", force_download=False)
    assert result == "DOM_OBJECT"
    assert call_log == ["download", "parse_dom"]

def test_get_dom_file_exists(monkeypatch):
    """Test that get_dom only parses when file exists and force_download is False."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: True)
    result = handler.get_dom(file_name, url="http://example.com", force_download=False)
    assert result == "DOM_OBJECT"
    assert call_log == ["parse_dom"]

def test_get_dom_force_download_missing_url(monkeypatch):
    """Test that get_dom raises ValueError when force_download is True and url is missing."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: None)
    monkeypatch.setattr(handler, "parse_dom", lambda path: None)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with pytest.raises(ValueError):
        handler.get_dom(file_name, url=None, force_download=True)

def test_get_dom_file_missing_missing_url(monkeypatch):
    """Test that get_dom raises ValueError when file does not exist, force_download is False, and url is missing."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: None)
    monkeypatch.setattr(handler, "parse_dom", lambda path: None)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with pytest.raises(ValueError):
        handler.get_dom(file_name, url=None, force_download=False)
