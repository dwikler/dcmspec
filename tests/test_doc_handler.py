"""Tests for the DocHandler base class in dcmspec.doc_handler."""
import logging
import os
import pytest
import requests
from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler

class DummyDocHandler(DocHandler):
    """Concrete subclass for testing DocHandler logic."""

    def load_document(self, *args, **kwargs):
        """Do nothing."""
        pass

def test_doc_handler_init_defaults():
    """Test DocHandler __init__ with default arguments."""
    handler = DummyDocHandler()
    assert isinstance(handler.logger, logging.Logger)
    assert isinstance(handler.config, Config)

def test_doc_handler_init_with_logger_and_config():
    """Test DocHandler __init__ with custom logger and config."""
    custom_logger = logging.getLogger("custom")
    custom_config = Config()
    handler = DummyDocHandler(config=custom_config, logger=custom_logger)
    assert handler.logger is custom_logger
    assert handler.config is custom_config

def test_doc_handler_init_type_errors():
    """Test DocHandler __init__ raises TypeError for invalid logger or config."""
    with pytest.raises(TypeError):
        DummyDocHandler(logger="not_a_logger")
    with pytest.raises(TypeError):
        DummyDocHandler(config="not_a_config")

def test_download_success(monkeypatch, tmp_path, caplog):
    """Test that download saves text file and logs info."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    class DummyResponse:
        text = "abc"
        status_code = 200
        def raise_for_status(self): pass

    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponse())
    with caplog.at_level("INFO"):
        result_path = handler.download("http://example.com", str(file_path))
    assert result_path == str(file_path)
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "abc"
    assert f"Downloading document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text

def test_download_success_binary(monkeypatch, tmp_path, caplog):
    """Test that download saves binary file when binary=True."""
    handler = DummyDocHandler()
    file_name = "test.pdf"
    file_path = tmp_path / file_name

    class DummyResponse:
        content = b"\x25PDF-1.4"
        status_code = 200
        def raise_for_status(self): pass

    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponse())
    with caplog.at_level("INFO"):
        result_path = handler.download("http://example.com", str(file_path), binary=True)
    assert result_path == str(file_path)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == b"\x25PDF-1.4"
    assert f"Downloading document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text

def test_download_failure_network(tmp_path, monkeypatch):
    """Test that download raises RuntimeError on network error."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    class DummyResponse:
        def raise_for_status(self): raise requests.exceptions.RequestException("fail")

    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponse())
    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", str(file_path))
    assert "Failed to download" in str(excinfo.value)

def test_download_failure_dir(monkeypatch):  # sourcery skip: simplify-generator
    """Test that download raises RuntimeError if directory creation fails."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = f"/nonexistent_dir/{file_name}"

    # Patch os.makedirs to always raise OSError
    monkeypatch.setattr("os.makedirs", lambda *a, **k: (_ for _ in ()).throw(OSError("cannot create dir")))

    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", file_path)
    assert "Failed to create directory for" in str(excinfo.value)
    assert "cannot create dir" in str(excinfo.value)

def test_download_failure_save(monkeypatch, tmp_path):
    """Test that download raises RuntimeError if saving the file fails."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    class DummyResponse:
        text = "abc"
        status_code = 200
        def raise_for_status(self): pass

    monkeypatch.setattr("requests.get", lambda url, timeout: DummyResponse())
    # Patch builtins.open to raise OSError
    import builtins
    original_open = builtins.open
    def fail_open(*args, **kwargs):
        # sourcery skip: no-conditionals-in-tests
        if args[0] == str(file_path):
            raise OSError("save failed")
        return original_open(*args, **kwargs)
    monkeypatch.setattr("builtins.open", fail_open)
    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", str(file_path))
    assert "Failed to save file" in str(excinfo.value)
    assert "save failed" in str(excinfo.value)