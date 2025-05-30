"""Tests for the XHTMLDocHandler class in dcmspec.xhtml_doc_handler."""
from bs4 import ParserRejectedMarkup
import os
import pytest
from requests.exceptions import RequestException
from dcmspec.xhtml_doc_handler import XHTMLDocHandler


class DummyResponseSuccess:
    """A dummy HTTP response object that simulates a successful requests.get call."""

    def __init__(self):
        """Initialize a successful dummy response."""
        self.text = "test content"
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

def test_fetch_url_content_success(monkeypatch):
    """Test that _fetch_url_content successfully downloads content."""
    handler = XHTMLDocHandler()
    # Patch request get method
    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponseSuccess())
    # Check that response content is returned
    assert handler._fetch_url_content("http://example.com") == "test content"

def test_fetch_url_content_failure(monkeypatch):
    """Test that _fetch_url_content successfully raises exception."""
    handler = XHTMLDocHandler()
    # Patch request get method
    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponseFailure())
    # Check that request exception is raised
    with pytest.raises(RequestException):
        handler._fetch_url_content("http://example.com")

def test_ensure_dir_exists_creates_directory():
    """Test that _ensure_dir_exists successfully creates the directory specified in path."""
    handler = XHTMLDocHandler()
    # Use the patched cache directory as the base (patch_dirs is autouse)
    cache_dir = handler.config.get_param("cache_dir")
    file_path = os.path.join(cache_dir, "standard", "file.xhtml")
    dir_path = os.path.join(cache_dir, "standard")
    assert not os.path.exists(dir_path)
    handler._ensure_dir_exists(file_path)
    assert os.path.exists(dir_path)

def test_save_content_cleans_and_writes():
    """Test that _save_content successfully cleans up and writes the content to the file."""
    handler = XHTMLDocHandler()
    cache_dir = handler.config.get_param("cache_dir")
    file_path = os.path.join(cache_dir, "standard", "file.xhtml")
    html_content = "A\u200bB\u00a0C"
    # Ensure the directory exists before saving
    handler._ensure_dir_exists(file_path)
    handler._save_content(str(file_path), html_content)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u200b" not in content
    assert "\u00a0" not in content
    assert "AB C" in content

def mock_ensure_dir_exists(path, call_log):
    """Mock _ensure_dir_exists method."""
    call_log.append(("ensure_dir_exists", path))

def mock_fetch_url_content(url, call_log):
    """Mock _fetch_url_content method."""
    call_log.append(("fetch_url_content", url))
    return "<html>content</html>"

def mock_save_content(path, content, call_log):
    """Mock _save_content method."""
    call_log.append(("save_content", path, content))

def test_download_success(monkeypatch, caplog):
    """Test that download calls helpers and logs info, and returns the correct file path."""
    handler = XHTMLDocHandler()
    cache_dir = handler.config.get_param("cache_dir")
    file_name = "test.xhtml"
    file_path = os.path.join(cache_dir, "standard", file_name)

    call_log = []

    monkeypatch.setattr(handler, "_ensure_dir_exists", lambda path: mock_ensure_dir_exists(path, call_log))
    monkeypatch.setattr(handler, "_fetch_url_content", lambda url: mock_fetch_url_content(url, call_log))
    monkeypatch.setattr(handler, "_save_content", lambda path, content: mock_save_content(path, content, call_log))

    with caplog.at_level("INFO"):
        result = handler.download("http://example.com", file_name)

    assert result == file_path
    assert call_log == [
        ("ensure_dir_exists", file_path),
        ("fetch_url_content", "http://example.com"),
        ("save_content", file_path, "<html>content</html>"),
    ]
    assert f"Downloading XHTML document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text


def fail_ensure_dir_exists(path):
    """Mock _ensure_dir_exists that always fails."""
    raise OSError("cannot create dir")

def fail_fetch_url_content(url):
    """Mock _fetch_url_content that always fails."""
    raise RequestException("fetch failed")

def fail_save_content(path, content):
    """Mock _save_content that always fails."""
    raise OSError("save failed")

def test_download_ensure_dir_fails(monkeypatch, caplog):
    """Test that download raises RuntimeError if _ensure_dir_exists fails."""
    handler = XHTMLDocHandler()
    cache_dir = handler.config.get_param("cache_dir")
    file_name = "test.xhtml"
    file_path = os.path.join(cache_dir, "standard", file_name)

    monkeypatch.setattr(handler, "_ensure_dir_exists", fail_ensure_dir_exists)
    monkeypatch.setattr(handler, "_fetch_url_content", lambda url: "<html>content</html>")
    monkeypatch.setattr(handler, "_save_content", lambda path, content: None)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_name)
    assert "Failed to create directory for" in str(excinfo.value)
    assert "cannot create dir" in str(excinfo.value)
    assert f"Failed to create directory for {file_path}: cannot create dir" in caplog.text

def test_download_fetch_url_fails(monkeypatch, caplog):
    """Test that download raises RuntimeError if _fetch_url_content fails."""
    handler = XHTMLDocHandler()
    file_name = "test.xhtml"

    monkeypatch.setattr(handler, "_ensure_dir_exists", lambda path: None)
    monkeypatch.setattr(handler, "_fetch_url_content", fail_fetch_url_content)
    monkeypatch.setattr(handler, "_save_content", lambda path, content: None)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_name)
    assert "Failed to download http://example.com: fetch failed" in str(excinfo.value)
    assert "Failed to download http://example.com: fetch failed" in caplog.text

def test_download_save_content_fails(monkeypatch, caplog):
    """Test that download raises RuntimeError if _save_content fails."""
    handler = XHTMLDocHandler()
    cache_dir = handler.config.get_param("cache_dir")
    file_name = "test.xhtml"
    file_path = os.path.join(cache_dir, "standard", file_name)

    monkeypatch.setattr(handler, "_ensure_dir_exists", lambda path: None)
    monkeypatch.setattr(handler, "_fetch_url_content", lambda url: "<html>content</html>")
    monkeypatch.setattr(handler, "_save_content", fail_save_content)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_name)
    assert "Failed to save file" in str(excinfo.value)
    assert "save failed" in str(excinfo.value)
    assert f"Failed to save file {file_path}: save failed" in caplog.text

def test_parse_dom_success(tmp_path, caplog):
    """Test that parse_dom reads and parses a valid XHTML file, logs info, and returns a BeautifulSoup object."""
    handler = XHTMLDocHandler()
    cache_dir = handler.config.get_param("cache_dir")
    file_path = os.path.join(cache_dir, "standard", "file.xhtml")
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
    cache_dir = handler.config.get_param("cache_dir")
    file_path = os.path.join(cache_dir, "standard", "nonexistent.xhtml")
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
    cache_dir = handler.config.get_param("cache_dir")
    file_path = os.path.join(cache_dir, "standard", "bad.xhtml")
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
    file_path = os.path.join(handler.config.get_param("cache_dir"), "standard", file_name)
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
    file_path = os.path.join(handler.config.get_param("cache_dir"), "standard", file_name)
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
    file_path = os.path.join(handler.config.get_param("cache_dir"), "standard", file_name)
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
