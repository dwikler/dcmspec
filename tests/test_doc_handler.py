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

    def raise_for_status(self):
        """Simulate a successful response."""
        if self._raise_exc:
            raise self._raise_exc

    def __enter__(self):
        """Simulate entering a context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Simulate exiting a context."""
        pass

    def iter_content(self, chunk_size=8192, decode_unicode=False):
        """Simulate iterating over content in chunks."""
        # For binary, yield bytes; for text, yield string if decode_unicode else bytes
        if decode_unicode:
            yield self.text
        else:
            yield self.content

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

def test_download_success(monkeypatch, tmp_path, caplog, dummy_response):
    """Test that download saves text file and logs info."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    monkeypatch.setattr("requests.get", lambda url, timeout, **kwargs: dummy_response())
    with caplog.at_level("INFO"):
        result_path = handler.download("http://example.com", str(file_path), progress_callback=None)
    assert result_path == str(file_path)
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "abc"
    assert f"Downloading document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text

def test_download_success_binary(monkeypatch, tmp_path, caplog, dummy_response):
    """Test that download saves binary file when binary=True."""
    handler = DummyDocHandler()
    file_name = "test.pdf"
    file_path = tmp_path / file_name

    monkeypatch.setattr("requests.get", lambda url, timeout, **kwargs: dummy_response(content=b"\x25PDF-1.4"))
    with caplog.at_level("INFO"):
        result_path = handler.download("http://example.com", str(file_path), binary=True)
    assert result_path == str(file_path)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == b"\x25PDF-1.4"
    assert f"Downloading document from http://example.com to {file_path}" in caplog.text
    assert f"Document downloaded to {file_path}" in caplog.text

def test_download_failure_network(tmp_path, monkeypatch, dummy_response):
    """Test that download raises RuntimeError on network error."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            raise_exc=requests.exceptions.RequestException("fail")
        )
    )
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

def test_download_failure_save(monkeypatch, tmp_path, dummy_response):
    """Test that download raises RuntimeError if saving the file fails."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    monkeypatch.setattr("requests.get", lambda url, timeout, **kwargs: dummy_response())
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

def test_download_progress_callback_text(monkeypatch, tmp_path, dummy_response):
    """Test that download calls progress_callback with correct percent values."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    # Simulate multiple chunks
    chunks = ["a", "b", "c"]
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            text="abc",
            chunks=chunks,
            headers={"content-length": "3"}
        )
    )

    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)

    handler.download("http://example.com", str(file_path), progress_callback=progress_callback)
    assert progress_values == [33, 66, 100]

def test_download_progress_observer_text(monkeypatch, tmp_path, dummy_response):
    """Test that download calls progress_observer with Progress objects and correct status."""
    from dcmspec.progress import Progress, ProgressStatus
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    # Simulate multiple chunks
    chunks = ["a", "b", "c"]
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            text="abc",
            chunks=chunks,
            headers={"content-length": "3"}
        )
    )

    progress_events = []
    def progress_observer(progress):
        progress_events.append(progress)

    handler.download("http://example.com", str(file_path), progress_observer=progress_observer)
    # Should get Progress objects with percent 33, 66, 100 and status DOWNLOADING
    assert [p.percent for p in progress_events] == [33, 66, 100]
    assert all(isinstance(p, Progress) for p in progress_events)
    assert all(p.status == ProgressStatus.DOWNLOADING for p in progress_events)

def test_download_progress_callback_single_large_chunk(monkeypatch, tmp_path, dummy_response):
    """Test that download calls progress_callback with 100% for a single large chunk (non-chunked download)."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name

    # Simulate a single chunk equal to the total content-length
    content = "a" * 1000
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            text=content,
            chunks=[content],
            headers={"content-length": "1000"}
        )
    )

    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)

    handler.download("http://example.com", str(file_path), progress_callback=progress_callback)
    # Should get exactly one progress update at 100%
    assert progress_values == [100]

def test_download_progress_callback_binary(monkeypatch, tmp_path, dummy_response):
    """Test that download calls progress_callback with correct percent values for binary downloads."""
    handler = DummyDocHandler()
    file_name = "test.pdf"
    file_path = tmp_path / file_name

    # Simulate multiple binary chunks
    chunks = [b"\x25", b"PDF", b"-1.4"]
    total_size = sum(len(chunk) for chunk in chunks)
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            content=b"".join(chunks), chunks=chunks, headers={"content-length": str(total_size)}
        ),
    )

    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)

    handler.download("http://example.com", str(file_path), binary=True, progress_callback=progress_callback)
    # Should get progress for each chunk: 28, 71, 100 (for 3 chunks of 7 bytes)
    assert progress_values[-1] == 100
    assert all(0 < p <= 100 for p in progress_values)
    assert len(progress_values) == 3

def test_download_progress_callback_unknown_length_no_header(monkeypatch, tmp_path, dummy_response):
    """Test progress_callback is called with -1 when content-length header is missing."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name
    chunks = ["a", "b", "c"]
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            text="abc", chunks=chunks, headers={}
        )
    )
    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)
    handler.download("http://example.com", str(file_path), progress_callback=progress_callback)
    assert progress_values == [-1]

def test_download_progress_callback_unknown_length_zero(monkeypatch, tmp_path, dummy_response):
    """Test progress_callback is called with -1 when content-length header is zero."""
    handler = DummyDocHandler()
    file_name = "test.txt"
    file_path = tmp_path / file_name
    chunks = ["a", "b", "c"]
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            text="abc", chunks=chunks, headers={"content-length": "0"}
        )
    )
    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)
    handler.download("http://example.com", str(file_path), progress_callback=progress_callback)
    assert progress_values == [-1]

def test_download_progress_callback_unknown_length_binary(monkeypatch, tmp_path, dummy_response):
    """Test progress_callback is called with -1 for binary download with unknown length."""
    handler = DummyDocHandler()
    file_name = "test.pdf"
    file_path = tmp_path / file_name
    binary_chunks = [b"a", b"b", b"c"]
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout, **kwargs: dummy_response(
            content=b"abc", chunks=binary_chunks, headers={}
        )
    )
    progress_values = []
    def progress_callback(percent):
        progress_values.append(percent)
    handler.download("http://example.com", str(file_path), binary=True, progress_callback=progress_callback)
    assert progress_values == [-1]