"""Tests for the XHTMLDocHandler class in dcmspec.xhtml_doc_handler."""
from bs4 import ParserRejectedMarkup
import os
import pytest
from requests.exceptions import RequestException
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
        
class DummyResponseFailure:
    """A dummy HTTP response object that simulates a failed requests.get call."""

    def raise_for_status(self): 
        """Simulate a failed request by raising an exception."""
        raise RequestException("fail")

def _standard_file_path(handler, file_name):
    """Return the standard file path for a given handler and file name."""
    cache_dir = handler.config.get_param("cache_dir")
    return os.path.join(cache_dir, "standard", file_name)

def test_download_cleans_xhtml(monkeypatch, caplog, dummy_response):
    """Test that download cleans ZWSP/NBSP and logs info, and returns the correct file path."""
    handler = XHTMLDocHandler()
    file_name = "test.xhtml"
    file_path = _standard_file_path(handler, file_name)

    # Patch request get method
    monkeypatch.setattr("requests.get", lambda url, timeout, **kwargs: dummy_response(text="A\u200bB\u00a0C"))

    with caplog.at_level("INFO"):
        # Call the download method
        result_path = handler.download("http://example.com", file_name, progress_observer=None)

    # Assert the file was created and contains the expected content
    assert result_path == file_path
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u200b" not in content
    assert "\u00a0" not in content
    assert "AB C" in content

    assert f"Downloading document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text


def test_parse_dom_success(tmp_path, caplog):
    """Test that parse_dom reads and parses a valid XHTML file, logs info, and returns a BeautifulSoup object."""
    handler = XHTMLDocHandler()
    file_path = _standard_file_path(handler, "file.xhtml")

    # Ensure the directory exists and write a simple XHTML file
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
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

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<root><tag>unclosed</root>")  # Malformed XML

    # Patch the BeautifulSoup used in the xhtml_doc_handler module
    monkeypatch.setattr("dcmspec.xhtml_doc_handler.BeautifulSoup", raise_bs4_parser_rejected_markup)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.parse_dom(file_path)
    assert "Failed to parse XHTML file" in str(excinfo.value)
    assert f"Failed to parse XHTML file {file_path}" in caplog.text

def test_load_document_force_download(monkeypatch):
    """Test that load_document downloads and parses when force_download is True."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name, **kwargs: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    result = handler.load_document(file_name, url="http://example.com", force_download=True)
    assert result == "DOM_OBJECT"
    assert call_log == ["download", "parse_dom"]

def test_load_document_progress_callback(monkeypatch):
    """Test that load_document adapts a legacy int progress callback to work with the observer API."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)
    # Patch download to call the observer as the real code would (with a Progress object)
    def fake_download(url, cache_file_name, progress_observer=None, **kwargs):
        class DummyProgress:
            percent = 88
        progress_observer(DummyProgress())
        return file_path
    monkeypatch.setattr(handler, "download", fake_download)
    monkeypatch.setattr(handler, "parse_dom", lambda path: "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    handler.load_document(file_name, url="http://example.com", force_download=True, progress_callback=progress_callback)
    assert progress_values == [88]

def test_load_document_progress_observer_class(monkeypatch):
    """Test that load_document works with a ProgressObserver class instance."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    class MyObserver:
        def __init__(self):
            self.values = []
        def __call__(self, progress):
            self.values.append(progress.percent)
    observer = MyObserver()
    def fake_download(url, cache_file_name, progress_observer=None, **kwargs):
        class DummyProgress:
            percent = 55
        progress_observer(DummyProgress())
        return file_path
    monkeypatch.setattr(handler, "download", fake_download)
    monkeypatch.setattr(handler, "parse_dom", lambda path: "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    handler.load_document(file_name, url="http://example.com", force_download=True, progress_observer=observer)
    assert observer.values == [55]

def test_load_document_file_missing(monkeypatch):
    """Test that load_document downloads and parses when file does not exist and force_download is False."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name, **kwargs: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    result = handler.load_document(file_name, url="http://example.com", force_download=False)
    assert result == "DOM_OBJECT"
    assert call_log == ["download", "parse_dom"]

def test_load_document_file_exists(monkeypatch):
    """Test that load_document only parses when file exists and force_download is False."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    file_path = _standard_file_path(handler, file_name)
    call_log = []
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name, **kwargs: call_log.append("download") or file_path)
    monkeypatch.setattr(handler, "parse_dom", lambda path: call_log.append("parse_dom") or "DOM_OBJECT")
    monkeypatch.setattr("os.path.exists", lambda path: True)
    result = handler.load_document(file_name, url="http://example.com", force_download=False)
    assert result == "DOM_OBJECT"
    assert call_log == ["parse_dom"]

def test_load_document_force_download_missing_url(monkeypatch):
    """Test that load_document raises ValueError when force_download is True and url is missing."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: None)
    monkeypatch.setattr(handler, "parse_dom", lambda path: None)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with pytest.raises(ValueError):
        handler.load_document(file_name, url=None, force_download=True)

def test_load_document_no_file_missing_url(monkeypatch):
    """Test that load_document raises ValueError when file does not exist and url is missing."""
    handler = XHTMLDocHandler()
    file_name = "file.xhtml"
    monkeypatch.setattr(handler, "download", lambda url, cache_file_name: None)
    monkeypatch.setattr(handler, "parse_dom", lambda path: None)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with pytest.raises(ValueError):
        handler.load_document(file_name, url=None, force_download=False)
