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
    # logger should have a StreamHandler attached
    assert any(isinstance(h, logging.StreamHandler) for h in handler.logger.handlers)

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

def test_doc_handler_custom_logger_no_handlers():
    """Test that a custom logger with no handlers gets a StreamHandler and level set to INFO."""
    custom_logger = logging.getLogger("no_handlers_logger")
    # Remove all handlers if any exist
    custom_logger.handlers.clear()
    # Set to a non-INFO level to check if it gets overwritten
    custom_logger.setLevel(logging.DEBUG)
    DummyDocHandler(logger=custom_logger)
    # Should have a StreamHandler attached
    assert any(isinstance(h, logging.StreamHandler) for h in custom_logger.handlers)
    # Should set level to INFO
    assert custom_logger.level == logging.INFO

def test_doc_handler_custom_logger_with_handlers():
    """Test that a custom logger with existing handlers does not get a new StreamHandler and level is unchanged."""
    custom_logger = logging.getLogger("with_handlers_logger")
    # Remove all handlers and add a dummy handler
    custom_logger.handlers.clear()
    dummy_handler = logging.StreamHandler()
    custom_logger.addHandler(dummy_handler)
    # Set to a non-INFO level
    custom_logger.setLevel(logging.WARNING)
    DummyDocHandler(logger=custom_logger)
    # Should not add another StreamHandler (still only one handler)
    assert custom_logger.handlers == [dummy_handler]
    # Should not change the logger's level
    assert custom_logger.level == logging.WARNING

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

def test_download_failure_dir(monkeypatch):
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
        if args[0] == str(file_path):
            raise OSError("save failed")
        return original_open(*args, **kwargs)
    monkeypatch.setattr("builtins.open", fail_open)
    with pytest.raises(RuntimeError) as excinfo:
        handler.download("http://example.com", str(file_path))
    assert "Failed to save file" in str(excinfo.value)
    assert "save failed" in str(excinfo.value)