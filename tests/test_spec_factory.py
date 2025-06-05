"""Tests for the SpecFactory class in dcmspec.spec_factory."""
import pytest
from anytree import Node
from dcmspec.spec_factory import SpecFactory
from dcmspec.config import Config
from dcmspec.spec_model import SpecModel

class DummyInputHandler:
    """A dummy input handler that simulates downloading and parsing input files."""

    def __init__(self):
        """Initialize the dummy input handler."""
        self.called = False

    def get_dom(self, cache_file_name, url=None, force_download=False):
        """Simulate getting a DOM from a file or URL."""
        self.called = True
        return "DOM"

class DummyTableParser:
    """A dummy table parser that simulates parsing a DOM into metadata and content nodes."""

    def __init__(self):
        """Initialize the dummy table parser."""
        self.called = False

    def parse(self, dom, table_id, include_depth, column_to_attr, name_attr, **kwargs):
        """Simulate parsing a DOM and returning dummy metadata and content nodes."""
        self.called = True
        # Return dummy metadata and content nodes as anytree Nodes
        metadata = Node("metadata")
        content = Node("content")
        return metadata, content

class DummyModelStore:
    """A dummy model store that simulates loading and saving SpecModel objects."""

    def __init__(self):
        """Initialize the dummy model store."""
        self.saved = None
        self.loaded = None
        self.load_should_fail = False

    def load(self, path):
        """Simulate loading a SpecModel from a file path."""
        if self.load_should_fail:
            raise IOError(f"Failed to load model from path: {path}")
        self.loaded = path
        # Return a SpecModel with anytree Nodes
        from anytree import Node
        return SpecModel(metadata=Node("metadata"), content=Node("content"))

    def save(self, model, path):
        """Simulate saving a SpecModel to a file path.

        Instead of actually writing to disk, this method records the model and path
        in the `self.saved` attribute as a tuple. This allows tests to verify that
        the save operation was called with the expected arguments, without performing
        any real file I/O.
        """
        self.saved = (model, path)


def test_init_defaults():
    """Test SpecFactory initializes with default components if none are provided."""
    factory = SpecFactory()
    from dcmspec.xhtml_doc_handler import XHTMLDocHandler
    from dcmspec.json_spec_store import JSONSpecStore
    from dcmspec.dom_table_spec_parser import DOMTableSpecParser

    assert isinstance(factory.input_handler, XHTMLDocHandler)
    assert isinstance(factory.model_store, JSONSpecStore)
    assert isinstance(factory.table_parser, DOMTableSpecParser)
    assert isinstance(factory.column_to_attr, dict)
    assert factory.column_to_attr == {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}
    assert factory.name_attr == "elem_name"
    assert isinstance(factory.config, Config)


def test_init_custom_components():
    """Test SpecFactory initializes with custom components."""
    ih = DummyInputHandler()
    ms = DummyModelStore()
    tp = DummyTableParser()
    config = Config()
    factory = SpecFactory(
        input_handler=ih,
        model_store=ms,
        table_parser=tp,
        column_to_attr={0: "elem_tag"},
        name_attr="elem_tag",
        config=config,
    )
    assert factory.input_handler is ih
    assert factory.model_store is ms
    assert factory.table_parser is tp
    assert factory.column_to_attr == {0: "elem_tag"}
    assert factory.name_attr == "elem_tag"
    assert factory.config is config

def test_init_type_error():
    """Test SpecFactory raises TypeError if config is not a Config instance."""
    with pytest.raises(TypeError):
        SpecFactory(config="not_a_config")

def test_from_url_default_json_file_name(monkeypatch, patch_dirs):
    """Test from_url uses default json_file_name if not provided."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    cache_file_name = "file.xhtml"
    # Do NOT provide json_file_name
    factory.from_url(
        url="http://example.com",
        cache_file_name=cache_file_name,
        table_id="table1",
        force_download=True,
        # json_file_name is omitted
    )
    expected_path = str(patch_dirs / "cache" / "model" / "file.json")
    assert ms.saved[1] == expected_path

def test_from_url_loads_from_cache(monkeypatch, patch_dirs):
    """Test from_url loads model from cache if present and not force_download."""
    ms = DummyModelStore()
    ms.load_should_fail = False
    factory = SpecFactory(model_store=ms)
    # Patch os.path.exists to always return True
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch config.get_param to return a dummy path
    model = factory.from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=False,
        json_file_name="file.json",
    )
    assert isinstance(model, SpecModel)
    expected_path = str(patch_dirs / "cache" / "model" / "file.json")
    assert ms.loaded == expected_path

def test_from_url_fallback_to_input(monkeypatch):
    """Test from_url falls back to input handler and parser if cache load fails."""
    ms = DummyModelStore()
    ms.load_should_fail = True
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch model_store.save to do nothing
    monkeypatch.setattr(ms, "save", lambda model, path: None)
    factory.from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=False,
        json_file_name="file.json",
    )
    assert ih.called
    assert tp.called

def test_from_url_force_download(monkeypatch):
    """Test from_url uses input handler and parser if force_download is True."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch model_store.save to do nothing
    monkeypatch.setattr(ms, "save", lambda model, path: None)
    factory.from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=True,
        json_file_name="file.json",
    )
    assert ih.called
    assert tp.called

def raise_save_failure(*args, **kwargs):
    """Simulate a save failure by raising an IOError."""
    raise IOError("Simulated save failure")

def test_from_url_save_failure(monkeypatch, capsys):
    """Test from_url handles failure of model_store.save gracefully."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    # Patch model_store.save to raise an exception
    monkeypatch.setattr(ms, "save", raise_save_failure)
    factory.from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=True,
        json_file_name="file.json",
    )
    captured = capsys.readouterr()
    assert "Warning: Failed to cache model" in captured.out
    assert "Simulated save failure" in captured.out
