"""Tests for the SpecFactory class in dcmspec.spec_factory."""
import logging
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
        self.logger = logging.getLogger("DummyInputHandler")
        self.cache_file_name = "file.xhtml"

    def get_dom(self, cache_file_name, url=None, force_download=False):
        """Simulate getting a DOM from a file or URL."""
        self.called = True
        return "DOM"

class NoCacheFileNameInputHandler(DummyInputHandler):
    """A dummy input handler without cache_file_name."""

    def __init__(self):
        """Initialize the no cache filename dummy input handler."""
        super().__init__()
        self.cache_file_name = None

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

def test_load_dom(monkeypatch):
    """Test load_dom returns the DOM and calls input_handler.get_dom."""
    ih = DummyInputHandler()
    factory = SpecFactory(input_handler=ih)
    dom = factory.load_dom(url="http://example.com", cache_file_name="file.xhtml", force_download=True)
    assert dom == "DOM"
    assert ih.called

def test_build_model(monkeypatch, patch_dirs):
    """Test build_model builds and saves the model, uses default json_file_name if not provided."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    dom = "DOM"
    factory.build_model(
        dom=dom,
        table_id="table1",
        url="http://example.com",
        # json_file_name is omitted
    )
    expected_path = str(patch_dirs / "cache" / "model" / "file.json")
    assert ms.saved[1] == expected_path
    assert tp.called

def test_build_model_with_custom_json_file_name(monkeypatch, patch_dirs):
    """Test build_model uses the provided custom json_file_name."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    dom = "DOM"
    custom_json_file_name = "custom_model.json"
    factory.build_model(
        dom=dom,
        table_id="table1",
        url="http://example.com",
        json_file_name=custom_json_file_name,
    )
    expected_path = str(patch_dirs / "cache" / "model" / custom_json_file_name)
    assert ms.saved[1] == expected_path
    assert tp.called

def test_build_model_loads_from_cache(monkeypatch, patch_dirs):
    """Test build_model loads model from cache if present and not force_parse."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    ms.load_should_fail = False
    factory = SpecFactory(model_store=ms, input_handler=ih)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    dom = "DOM"
    model = factory.build_model(
        dom=dom,
        table_id="table1",
        url="http://example.com",
        json_file_name="file.json",
        force_parse=False,
    )
    assert isinstance(model, SpecModel)
    expected_path = str(patch_dirs / "cache" / "model" / "file.json")
    assert ms.loaded == expected_path

def test_build_model_fallback_to_parser(monkeypatch):
    """Test build_model falls back to parser if cache load fails."""
    ms = DummyModelStore()
    ms.load_should_fail = True
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch model_store.save to do nothing
    monkeypatch.setattr(ms, "save", lambda model, path: None)
    dom = "DOM"
    factory.build_model(
        dom=dom,
        table_id="table1",
        url="http://example.com",
        json_file_name="file.json",
    )
    assert tp.called

def test_build_model_force_parse(monkeypatch):
    """Test build_model parses and saves even if cache exists when force_parse is True."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch model_store.save to do nothing
    monkeypatch.setattr(ms, "save", lambda model, path: None)
    dom = "DOM"
    factory.build_model(
        dom=dom,
        table_id="table1",
        url="http://example.com",
        json_file_name="file.json",
        force_parse=True,
    )
    assert tp.called

def raise_save_failure(*args, **kwargs):
    """Simulate a save failure by raising an IOError."""
    raise IOError("Simulated save failure")

def test_build_model_save_failure(monkeypatch, caplog):
    """Test build_model handles failure of model_store.save gracefully."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    monkeypatch.setattr("os.path.exists", lambda path: False)
    # Patch model_store.save to raise an exception
    monkeypatch.setattr(ms, "save", raise_save_failure)
    dom = "DOM"
    with caplog.at_level("WARNING"):
        factory.build_model(
            dom=dom,
            table_id="table1",
            url="http://example.com",
            json_file_name="file.json",
        )
    log_output = caplog.text
    assert "Failed to cache model" in log_output
    assert "Simulated save failure" in log_output

@pytest.fixture
def fake_load_and_build(monkeypatch):
    """Fixture providing fake load_dom and build_model methods for SpecFactory tests.

    Returns:
        tuple: (called, fake_load_dom, fake_build_model)
            - called: dict to record the arguments with which the fakes are called.
            - fake_load_dom: function to patch load_dom, records its arguments and returns a fake dom.
            - fake_build_model: function to patch build_model, records its arguments and returns a fake model.

    Usage:
        called, fake_load_dom, fake_build_model = fake_load_and_build
        monkeypatch.setattr(factory, "load_dom", fake_load_dom)
        monkeypatch.setattr(factory, "build_model", fake_build_model)

    """
    called = {}

    def fake_load_dom(url, cache_file_name, force_download):
        called["load_dom"] = (url, cache_file_name, force_download)
        return "FAKE_DOM"

    def fake_build_model(dom, table_id, url, json_file_name, include_depth, force_parse, **kwargs):
        called["build_model"] = (dom, table_id, url, json_file_name, include_depth, force_parse)
        return "FAKE_MODEL"

    return called, fake_load_dom, fake_build_model

def test_build_model_raises_if_no_json_or_cache(monkeypatch):
    """Test build_model raises ValueError if neither json_file_name nor cache_file_name is set."""
    ms = DummyModelStore()
    ih = NoCacheFileNameInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)
    dom = "DOM"
    with pytest.raises(ValueError, match="input_handler.cache_file_name not set"):
        factory.build_model(
            dom=dom,
            table_id="table1",
            url="http://example.com",
            # json_file_name is omitted
        )

def test_create_model(monkeypatch, fake_load_and_build):
    """Test create_model uses default force_download=False when not specified."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)

    called, fake_load_dom, fake_build_model = fake_load_and_build
    monkeypatch.setattr(factory, "load_dom", fake_load_dom)
    monkeypatch.setattr(factory, "build_model", fake_build_model)

    # Do not pass force_download, should default to False
    result = factory.create_model(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        json_file_name="file.json",
        include_depth=2,
    )
    assert result == "FAKE_MODEL"
    # Assert that force_download is False by default
    assert called["load_dom"] == ("http://example.com", "file.xhtml", False)
    assert called["build_model"] == ("FAKE_DOM", "table1", "http://example.com", "file.json", 2, False)

def test_create_model_force_download(monkeypatch, fake_load_and_build):
    """Test create_model uses force_download=True when specified."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)

    called, fake_load_dom, fake_build_model = fake_load_and_build
    monkeypatch.setattr(factory, "load_dom", fake_load_dom)
    monkeypatch.setattr(factory, "build_model", fake_build_model)

    result = factory.create_model(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=True,
        json_file_name="file.json",
        include_depth=2,
    )
    assert result == "FAKE_MODEL"
    assert called["load_dom"] == ("http://example.com", "file.xhtml", True)
    assert called["build_model"] == ("FAKE_DOM", "table1", "http://example.com", "file.json", 2, True)

def test_create_model_force_parse(monkeypatch, fake_load_and_build):
    """Test create_model uses force_parse=True and it takes precedence over force_download."""
    ms = DummyModelStore()
    ih = DummyInputHandler()
    tp = DummyTableParser()
    factory = SpecFactory(model_store=ms, input_handler=ih, table_parser=tp)

    called, fake_load_dom, fake_build_model = fake_load_and_build
    monkeypatch.setattr(factory, "load_dom", fake_load_dom)
    monkeypatch.setattr(factory, "build_model", fake_build_model)

    result = factory.create_model(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table1",
        force_download=False,
        force_parse=True,
        json_file_name="file.json",
        include_depth=2,
    )
    assert result == "FAKE_MODEL"
    assert called["load_dom"] == ("http://example.com", "file.xhtml", False)
    assert called["build_model"] == ("FAKE_DOM", "table1", "http://example.com", "file.json", 2, True)