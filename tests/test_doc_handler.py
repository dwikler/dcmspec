"""Tests for the DocHandler abstract base class in dcmspec.doc_handler."""
import logging
import pytest
from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler

class DummyDocHandler(DocHandler):
    """Concrete subclass for testing DocHandler __init__ logic."""

    def get_dom(self, file_path: str):
        """Do nothing."""
        pass
    def download(self, url: str, file_path: str):
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