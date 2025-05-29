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