"""Tests for the IODSpecBuilder class in dcmspec.iod_spec_builder."""
import pytest
from anytree import Node
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_model import SpecModel

class DummyFactory:
    """A dummy factory that returns a fixed model for build_model and load_dom."""

    def __init__(self):
        """Initialize."""
        self.called = []

    def load_dom(self, url, cache_file_name, force_download=False):
        """Patch loading the DOM."""
        self.called.append(("load_dom", url, cache_file_name, force_download))
        return "FAKE_DOM"

    def build_model(self, dom, table_id, url, json_file_name, **kwargs):
        """Patch building the model."""
        self.called.append(("build_model", dom, table_id, url, json_file_name))
        metadata = self._create_metadata_node()
        content = Node("content")
        # Add a node with a ref attribute
        iod_node = Node("iod_node", parent=content)
        setattr(iod_node, "ref", "PATIENT")
        # Add a dummy module node for the referenced module
        module_content = Node("content")
        module_attr = Node("attr", parent=module_content)
        setattr(module_attr, "attr1", "Value1")
        setattr(module_attr, "attr2", "Value2")
        module_metadata = self._create_metadata_node()
        module_model = SpecModel(metadata=module_metadata, content=module_content)
        # Return a model with a content node and a referenced module node
        if table_id == "table_IOD":
            return SpecModel(metadata=metadata, content=content)
        else:
            return module_model

    def _create_metadata_node(self):
        # Create a dummy metadata node
        result = Node("metadata")
        result.header = ["Attr1", "Attr2"]
        result.column_to_attr = {0: "attr1", 1: "attr2"}
        return result

    def table_parser(self):
        """Patch for compatibility."""
        return self

    def get_table_id_from_section(self, dom, section_id):
        """Patch table_id retrieval."""
        # Always return a dummy table id for the referenced module
        return "table_PATIENT" if section_id == "sect_PATIENT" else None

class DummyConfig:
    """A dummy Config that returns a cache directory."""

    def __init__(self, cache_dir="cache"):
        """Initialize dummy Config."""
        self._cache_dir = cache_dir
    def get_param(self, key):
        """Patch."""
        if key == "cache_dir":
            return self._cache_dir
        raise KeyError(key)
    
class DummyModelStore:
    """A dummy ModelStore that returns a cached model and can record saves."""

    def __init__(self):
        """Initialize dummy ModelStore."""
        self.saved = {}

    def load(self, path):
        """Patch."""
        return "CACHED_MODEL"

    def save(self, model, path):
        """Record the model and path in the self.saved dict."""
        self.saved["model"] = model
        self.saved["path"] = path
        
def test_iod_spec_builder_combines_iod_and_module(monkeypatch):
    """Test IODSpecBuilder combines IOD and module models correctly."""
    factory = DummyFactory()
    # Patch table_parser on the factory to our dummy
    factory.table_parser = factory
    # Add a dummy config for cache_dir to support module cache loading
    factory.config = DummyConfig(cache_dir="cache")
    # Add a dummy model_store to support module cache loading
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    model = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # The expanded model should have a content node with the iod_node and the module's attr as children
    iod_node = next(iter(model.content.children))
    assert getattr(iod_node, "ref", None) == "PATIENT"
    # The module's attribute node should be a child of the iod_node
    module_attr = next(iter(iod_node.children))
    assert getattr(module_attr, "attr1", None) == "Value1"
    assert getattr(module_attr, "attr2", None) == "Value2"

def test_iod_spec_builder_no_referenced_modules(monkeypatch):
    """Test IODSpecBuilder raises if no referenced modules are found."""
    class NoRefFactory(DummyFactory):
        def build_model(self, dom, table_id, url, json_file_name, **kwargs):
            metadata = Node("metadata")
            metadata.header = ["Attr1", "Attr2"]
            metadata.column_to_attr = {0: "attr1", 1: "attr2"}
            content = Node("content")
            # No node with a ref attribute
            return SpecModel(metadata=metadata, content=content)
    factory = NoRefFactory()
    factory.table_parser = factory
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    with pytest.raises(RuntimeError, match="No module models were found"):
        builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name=None,
        )

def test_iod_spec_builder_missing_module_table(monkeypatch):
    """Test IODSpecBuilder skips missing module tables and raises if none found."""
    class MissingTableFactory(DummyFactory):
        def get_table_id_from_section(self, dom, section_id):
            return None  # Always missing
    factory = MissingTableFactory()
    factory.table_parser = factory
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    with pytest.raises(RuntimeError, match="No module models were found"):
        builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name=None,
        )

def test_iod_spec_builder_saves_expanded_model(monkeypatch, tmp_path):
    """Test IODSpecBuilder saves the expanded model if json_file_name is provided."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    builder.iod_factory.model_store = factory.model_store

    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    model = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name="expanded.json",
    )
    # The model should have been saved
    saved = factory.model_store.saved
    assert "model" in saved
    assert "path" in saved
    assert saved["path"].endswith("expanded.json")
    # The saved model should be the same as the returned model
    assert saved["model"] is model

def test_iod_spec_builder_save_failure_logs_warning(monkeypatch, tmp_path, caplog):
    """Test IODSpecBuilder logs a warning if saving the expanded model fails."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    class FailingModelStore(DummyModelStore):
        def save(self, model, path):
            raise IOError("Simulated save failure")

    factory.model_store = FailingModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    builder.iod_factory.model_store = factory.model_store

    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with caplog.at_level("WARNING"):
        model = builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name="expanded.json",
        )
    # The model should still be returned
    assert isinstance(model, SpecModel)
    # The warning should be logged
    assert "Failed to cache expanded model to" in caplog.text
    assert "Simulated save failure" in caplog.text

def test_iod_spec_builder_no_save_when_no_json_file(monkeypatch, tmp_path, caplog):
    """Test IODSpecBuilder does not call save if json_file_name is not specified and logs an info message."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    builder.iod_factory.model_store = factory.model_store

    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with caplog.at_level("INFO"):
        model = builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name=None,
        )
    assert isinstance(model, SpecModel)
    # The model should NOT have been saved
    assert factory.model_store.saved == {}
    # Should log an info message about not caching
    assert "No json_file_name specified; IOD model not cached." in caplog.text

def test_iod_spec_builder_load_cache_success(monkeypatch, tmp_path):
    """Test IODSpecBuilder returns cached model if available."""
    factory = DummyFactory()
    factory.table_parser = factory

    # Set the cache_dir for DummyConfig to tmp_path
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    # Patch os.path.exists to always return True
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch model_store.load to return a dummy model
    factory.model_store = DummyModelStore()
    builder.iod_factory.model_store = factory.model_store
    result = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name="dummy.json",
    )
    assert result == "CACHED_MODEL"

def test_iod_spec_builder_load_cache_failure(monkeypatch, tmp_path, caplog):
    """Test IODSpecBuilder logs a warning if loading the cached model or a module model fails."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    class FailingModelStore(DummyModelStore):
        def load(self, path):
            raise IOError("Simulated load failure")

    factory.model_store = FailingModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    builder.iod_factory.model_store = factory.model_store

    # Patch os.path.exists to always return True (simulate cache exists)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    with caplog.at_level("WARNING"):
        model = builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name="expanded.json",
        )
    # The model should still be returned (built, not loaded)
    assert isinstance(model, SpecModel)
    # The warnings for both expanded IOD and Module model should be logged
    assert (
        "Failed to load expanded IOD model from cache" in caplog.text
        or "Failed to load expanded model from cache" in caplog.text
    )
    assert "Failed to load module model from cache" in caplog.text
    assert "Simulated load failure" in caplog.text