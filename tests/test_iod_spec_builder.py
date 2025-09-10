"""Tests for the IODSpecBuilder class in dcmspec.iod_spec_builder."""
import pytest
from anytree import Node
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.progress import Progress, ProgressStatus
from dcmspec.spec_model import SpecModel
from dcmspec.module_registry import ModuleRegistry

@pytest.fixture(autouse=True)
def patch_get_table_id_from_section(monkeypatch):
    """Automatically patch get_table_id_from_section for all tests in this module."""
    def get_table_id_from_section(self, dom, section_id):
        if "PATIENT" in section_id:
            return "table_PATIENT"
        elif "STUDY" in section_id:
            return "table_STUDY"
        return None
    # Patch for all tests in this module
    monkeypatch.setattr("dcmspec.iod_spec_builder.DOMUtils.get_table_id_from_section", get_table_id_from_section)


class DummyFactory:
    """A dummy factory that returns a fixed model for build_model and load_dom."""

    def __init__(self, ref_value="PATIENT"):
        """Initialize with a configurable ref_value or list of ref_values for the IOD node(s)."""
        self.called = []
        # Accept either a single ref_value or a list of ref_values
        if isinstance(ref_value, (list, tuple)):
            self.ref_values = list(ref_value)
        else:
            self.ref_values = [ref_value]

    def load_document(self, url, cache_file_name, force_download=False, progress_observer=None, progress_callback=None):
        """Patch loading the document.

        Note: This dummy is meant to be called through a higher-level function
        (like IODSpecBuilder.build_from_url or SpecFactory.create_model) that adapts
        a legacy int progress_callback to a progress_observer. Only progress_observer
        is called here, never progress_callback. If you call this dummy directly with
        only progress_callback set, progress will not be reported.
        """
        self.called.append(("load_document", url, cache_file_name, force_download))
        if progress_observer:
            progress_observer(Progress(42))
        # Do NOT call progress_callback here.
        return "FAKE_DOM"

    def build_model(self, doc_object, table_id, url, json_file_name, **kwargs):
        """Patch building the model with configurable referenced modules."""
        self.called.append(("build_model", doc_object, table_id, url, json_file_name))
        metadata = self._create_metadata_node()
        # sourcery skip: extract-method, remove-unnecessary-else, swap-if-else-branches
        if table_id == "table_IOD":
            content = Node("content")
            # Add nodes with ref attributes from self.ref_values
            for ref in self.ref_values:
                module_node = Node(f"module_node_{ref}", parent=content)
                setattr(module_node, "ref", ref)
            return SpecModel(metadata=metadata, content=content)
        else:
            # Build a module model (for any referenced module)
            module_content = Node("content")
            module_attr = Node("attr", parent=module_content)
            setattr(module_attr, "attr1", "Value1")
            setattr(module_attr, "attr2", "Value2")
            module_metadata = self._create_metadata_node()
            return SpecModel(metadata=module_metadata, content=module_content)

    def _create_metadata_node(self):
        # Create a dummy metadata node
        result = Node("metadata")
        result.header = ["Attr1", "Attr2"]
        result.column_to_attr = {0: "attr1", 1: "attr2"}
        result.table_id = "table_IOD"
        return result

    def table_parser(self):
        """Patch for compatibility."""
        return self

class CustomRefFactory(DummyFactory):
    """A dummy factory that sets 'reference' instead of 'ref' for custom ref_attr tests."""

    def build_model(self, doc_object, table_id, url, json_file_name, **kwargs):
        """Patch building the model with custom reference attribute."""
        metadata = self._create_metadata_node()
        content = Node("content")
        iod_node = Node("iod_node", parent=content)
        setattr(iod_node, "reference", "PATIENT")
        module_content = Node("content")
        module_attr = Node("attr", parent=module_content)
        setattr(module_attr, "attr1", "Value1")
        setattr(module_attr, "attr2", "Value2")
        module_metadata = self._create_metadata_node()
        module_model = SpecModel(metadata=module_metadata, content=module_content)
        if table_id == "table_IOD":
            return SpecModel(metadata=metadata, content=content)
        else:
            return module_model

class NoRefFactory(DummyFactory):
    """A dummy factory that returns a model with no reference attribute for negative tests."""

    def build_model(self, doc_object, table_id, url, json_file_name, **kwargs):
        """Patch building the model with no reference attribute."""
        metadata = Node("metadata")
        metadata.header = ["Attr1", "Attr2"]
        metadata.column_to_attr = {0: "attr1", 1: "attr2"}
        content = Node("content")
        # No node with a ref attribute
        return SpecModel(metadata=metadata, content=content)

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
        self.cached_model = None

    def load(self, path):
        """Load a dummy cached model."""
        if self.cached_model is None:
            metadata = Node("metadata")
            content = Node("content")
            self.cached_model = SpecModel(metadata=metadata, content=content)
            self.cached_model.logger = None
        return self.cached_model

    def save(self, model, path):
        """Record the model and path in the self.saved dict."""
        self.saved["model"] = model
        self.saved["path"] = path

class CustomModelStore(DummyModelStore):
    """A dummy ModelStore that returns specific models based on path."""

    def __init__(self, iod_model, module_models: dict):
        """Initialize with specific models to return."""
        super().__init__()
        self._iod_model = iod_model
        self._module_models = module_models  # dict: table_id -> module_model

    def load(self, path):
        """Return the iod_model or the correct module_model based on path."""
        if path.endswith("dummy.json"):
            return self._iod_model
        for table_id, module_model in self._module_models.items():
            if path.endswith(f"{table_id}.json"):
                return module_model
        return super().load(path)
    
class RegistryOnlyModelStore(DummyModelStore):
    """Dummy ModelStore that raises if asked to load a module model from cache.

    Ensuring that the registry is used for module models.
    """
    
    def __init__(self, iod_model, forbidden_table_ids=None):
        """Initialize with specific iod_model and forbidden table_ids."""
        super().__init__()
        self._iod_model = iod_model
        self._forbidden_table_ids = forbidden_table_ids or []

    def load(self, path):
        """Return the iod_model or raise if a forbidden module is requested."""
        if path.endswith("dummy.json"):
            return self._iod_model
        for table_id in self._forbidden_table_ids:
            if path.endswith(f"{table_id}.json"):
                raise AssertionError(f"Should not load module {table_id} from cache when registry is present")
        return super().load(path)

def test_iod_spec_builder_combines_iod_and_module():
    """Test IODSpecBuilder combines IOD and module models correctly."""
    factory = DummyFactory(ref_value=["PATIENT", "STUDY"])
    # Patch table_parser on the factory to our dummy
    factory.table_parser = factory
    # Add a dummy config for cache_dir to support module cache loading
    factory.config = DummyConfig(cache_dir="cache")
    # Add a dummy model_store to support module cache loading
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)

    model, _ = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # The expanded model should have a content node with the iod_nodes and the module's attr as children
    iod_nodes = list(model.content.children)
    refs = [getattr(node, "ref", None) for node in iod_nodes]
    assert "PATIENT" in refs
    assert "STUDY" in refs
    # For each iod_node, check that the module's attribute node is a child of the iod_node
    assert all(
        any(
            getattr(module_attr, "attr1", None) == "Value1" and
            getattr(module_attr, "attr2", None) == "Value2"
            for module_attr in iod_node.children
        )
        for iod_node in iod_nodes
    )

def test_iod_spec_builder_registry_mode():
    """Test IODSpecBuilder in registry/reference mode shares module models via ModuleRegistry."""
    factory = DummyFactory(ref_value=["PATIENT", "STUDY"])
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    registry = ModuleRegistry()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory, module_registry=registry)

    iod_model, module_models = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # The IOD model should not be expanded, but should have table_id set on the iod_nodes
    iod_nodes = list(iod_model.content.children)
    refs = [getattr(node, "ref", None) for node in iod_nodes]
    assert "PATIENT" in refs
    assert "STUDY" in refs
    # The module_models dict should be keyed by table_id and contain both module models
    assert "table_PATIENT" in module_models
    assert "table_STUDY" in module_models
    # The registry should also contain both module models
    assert "table_PATIENT" in registry
    assert "table_STUDY" in registry
    assert registry["table_PATIENT"] is module_models["table_PATIENT"]
    assert registry["table_STUDY"] is module_models["table_STUDY"]
    # The module's attribute node should be present in each module model
    assert all(
        any(
            getattr(module_attr, "attr1", None) == "Value1" and
            getattr(module_attr, "attr2", None) == "Value2"
            for module_attr in module_models[table_id].content.children
        )
        for table_id in ["table_PATIENT", "table_STUDY"]
    )

def test_build_from_url_normalizes_plain_text_ref(monkeypatch):
    """Test build_from_url normalizes plain text ref to sect_... and passes to get_table_id_from_section."""
    factory = DummyFactory(ref_value="C.7.1.1")
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)

    # Patch DOMUtils.get_table_id_from_section to record calls
    called_section_ids = []
    def fake_get_table_id_from_section(dom, section_id):
        called_section_ids.append(section_id)
        return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", fake_get_table_id_from_section)

    builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # Should have called get_table_id_from_section with normalized plain text
    assert "sect_C.7.1.1" in called_section_ids

def test_build_from_url_normalizes_html_anchor_ref(monkeypatch):
    """Test build_from_url normalizes HTML anchor ref and passes to get_table_id_from_section."""
    html_anchor = '<a class="xref" href="#sect_C.7.1.1">Patient Module</a>'
    factory = DummyFactory(ref_value=html_anchor)
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)

    # Patch DOMUtils.get_table_id_from_section to record calls
    called_section_ids = []
    def fake_get_table_id_from_section(dom, section_id):
        called_section_ids.append(section_id)
        return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", fake_get_table_id_from_section)

    builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # Should have called get_table_id_from_section with normalized HTML anchor
    assert "sect_C.7.1.1" in called_section_ids

def test_iod_spec_builder_custom_ref_attr(monkeypatch):
    """Test IODSpecBuilder works with a custom reference attribute name using DummyFactory."""
    factory = CustomRefFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory, ref_attr="reference")
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")

    model, _ = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    iod_node = next(iter(model.content.children))
    assert getattr(iod_node, "reference", None) == "PATIENT"
    module_attr = next(iter(iod_node.children))
    assert getattr(module_attr, "attr1", None) == "Value1"
    assert getattr(module_attr, "attr2", None) == "Value2"  

def test_iod_spec_builder_no_referenced_modules(monkeypatch):
    """Test IODSpecBuilder raises if no referenced modules are found."""
    factory = NoRefFactory()
    factory.table_parser = factory
    # Add a dummy config for cache_dir to support module cache loading
    factory.config = DummyConfig(cache_dir="cache")
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
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")  # <-- Add this line

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: None)

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

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")
    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    model, _ = builder.build_from_url(
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

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")
    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with caplog.at_level("WARNING"):
        model, _ = builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name="expanded.json",
        )
    # The model should still be returned
    assert isinstance(model, SpecModel)
    # The warning should be logged
    assert "Failed to cache model to" in caplog.text
    assert "Simulated save failure" in caplog.text

def test_iod_spec_builder_no_save_when_no_json_file(monkeypatch, tmp_path, caplog):
    """Test IODSpecBuilder does not call save if json_file_name is not specified and logs an info message."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    builder.iod_factory.model_store = factory.model_store

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")
    # Patch os.path.exists to always return False (force build, not cache)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with caplog.at_level("INFO"):
        model, _ = builder.build_from_url(
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
    model, _ = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name="dummy.json",
    )
    # The result should be a SpecModel loaded from cache
    assert isinstance(model, SpecModel)
    assert model is factory.model_store.load("dummy.json")

def test_iod_spec_builder_load_cache_with_registry(monkeypatch, tmp_path):
    """Test IODSpecBuilder loads from cache when a registry is passed as arg, with two modules."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    # Prepare dummy IOD and module models
    iod_model = SpecModel(metadata=Node("metadata"), content=Node("content"))
    module_model_patient = SpecModel(metadata=Node("metadata"), content=Node("content"))
    module_model_study = SpecModel(metadata=Node("metadata"), content=Node("content"))
    # Add two module nodes to the IOD model
    # sourcery skip: extract-duplicate-method
    iod_node_patient = Node("iod_node_patient", parent=iod_model.content)
    setattr(iod_node_patient, "ref", "PATIENT")
    setattr(iod_node_patient, "table_id", "table_PATIENT")
    iod_node_study = Node("iod_node_study", parent=iod_model.content)
    setattr(iod_node_study, "ref", "STUDY")
    setattr(iod_node_study, "table_id", "table_STUDY")

    # CustomModelStore returns the correct module model for each table
    module_models_dict = {
        "table_PATIENT": module_model_patient,
        "table_STUDY": module_model_study,
    }
    factory.model_store = CustomModelStore(iod_model, module_models_dict)

    registry = ModuleRegistry()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory, module_registry=registry)
    builder.iod_factory.model_store = factory.model_store
    builder.module_factory.model_store = factory.model_store

    # Patch os.path.exists to always return True
    monkeypatch.setattr("os.path.exists", lambda path: True)

    model, module_models = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name="dummy.json",
    )
    # The result should be a SpecModel loaded from cache
    assert isinstance(model, SpecModel)
    assert model is iod_model
    # The module_models dict should be present and contain both cached module models
    assert module_models is not None
    assert "table_PATIENT" in module_models
    assert "table_STUDY" in module_models
    assert module_models["table_PATIENT"] is module_model_patient
    assert module_models["table_STUDY"] is module_model_study
    # The registry should also contain both module models
    assert "table_PATIENT" in registry
    assert "table_STUDY" in registry
    assert registry["table_PATIENT"] is module_model_patient
    assert registry["table_STUDY"] is module_model_study

def test_iod_spec_builder_load_iod_cache_and_reuse_module_from_registry(monkeypatch, tmp_path):
    """Test IODSpecBuilder loads IOD from cache and reuses modules from registry."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir=str(tmp_path))

    # Prepare dummy IOD and module models
    iod_model = SpecModel(metadata=Node("metadata"), content=Node("content"))
    module_model_patient = SpecModel(metadata=Node("metadata"), content=Node("content"))
    module_model_study = SpecModel(metadata=Node("metadata"), content=Node("content"))
    # Add two module nodes to the IOD model
    # sourcery skip: extract-duplicate-method
    iod_node_patient = Node("iod_node_patient", parent=iod_model.content)
    setattr(iod_node_patient, "ref", "PATIENT")
    setattr(iod_node_patient, "table_id", "table_PATIENT")
    iod_node_study = Node("iod_node_study", parent=iod_model.content)
    setattr(iod_node_study, "ref", "STUDY")
    setattr(iod_node_study, "table_id", "table_STUDY")

    # Pre-populate the registry with both module models
    registry = ModuleRegistry()
    registry["table_PATIENT"] = module_model_patient
    registry["table_STUDY"] = module_model_study

    # Use RegistryOnlyModelStore to ensure cache is not used for modules
    factory.model_store = RegistryOnlyModelStore(iod_model, forbidden_table_ids=["table_PATIENT", "table_STUDY"])

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory, module_registry=registry)
    builder.iod_factory.model_store = factory.model_store
    builder.module_factory.model_store = factory.model_store

    # Patch os.path.exists to always return True
    monkeypatch.setattr("os.path.exists", lambda path: True)

    model, module_models = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name="dummy.json",
    )
    # The result should be a SpecModel loaded from cache
    assert isinstance(model, SpecModel)
    assert model is iod_model
    # The module_models dict should be present and contain the registry module models
    assert module_models is not None
    assert "table_PATIENT" in module_models
    assert "table_STUDY" in module_models
    assert module_models["table_PATIENT"] is module_model_patient
    assert module_models["table_STUDY"] is module_model_study
    # The registry should also contain both module models
    assert "table_PATIENT" in registry
    assert "table_STUDY" in registry
    assert registry["table_PATIENT"] is module_model_patient
    assert registry["table_STUDY"] is module_model_study

def test_iod_spec_builder_registry_reuse():
    """Test that IODSpecBuilder reuses one module from registry and builds the other."""
    factory = DummyFactory(ref_value=["PATIENT", "STUDY"])
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    registry = ModuleRegistry()

    # Pre-populate the registry with only PATIENT
    module_model_patient = SpecModel(metadata=Node("metadata"), content=Node("content"))
    registry["table_PATIENT"] = module_model_patient

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory, module_registry=registry)

    iod_model, module_models = builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        force_download=False,
        json_file_name=None,
    )
    # The module_models dict should be present and contain both modules
    assert module_models is not None
    assert "table_PATIENT" in module_models
    assert "table_STUDY" in module_models
    # PATIENT should be reused from registry, STUDY should be freshly built
    assert module_models["table_PATIENT"] is module_model_patient
    assert registry["table_PATIENT"] is module_model_patient
    assert registry["table_STUDY"] is module_models["table_STUDY"]
    # STUDY should be a SpecModel instance
    assert isinstance(module_models["table_STUDY"], SpecModel)
    # The two module models should not be the same object
    assert module_models["table_PATIENT"] is not module_models["table_STUDY"]

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

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")
    # Patch os.path.exists to always return True (simulate cache exists)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    with caplog.at_level("WARNING"):
        model, _ = builder.build_from_url(
            url="http://example.com",
            cache_file_name="file.xhtml",
            table_id="table_IOD",
            force_download=False,
            json_file_name="expanded.json",
        )
    # The model should still be returned (built, not loaded)
    assert isinstance(model, SpecModel)
    # The warnings for both expanded IOD and Module model should be logged
    assert "Failed to load IOD model from cache" in caplog.text
    assert "Failed to load module model from cache" in caplog.text
    assert "Simulated load failure" in caplog.text

def test_iod_spec_builder_progress_callback(monkeypatch):
    """Test that IODSpecBuilder.build_from_url passes and calls progress_callback."""
    from dcmspec.iod_spec_builder import IODSpecBuilder

    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()

    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)

    # Patch DOMUtils.get_table_id_from_section to always return "table_PATIENT"
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")

    progress_values = []
    def legacy_callback(percent):
        progress_values.append(percent)
    builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        progress_callback=legacy_callback
    )

    assert progress_values  # Should be called at least once
    # Should be int values
    assert all(isinstance(val, int) for val in progress_values)

def test_iod_spec_builder_progress_observer(monkeypatch):
    """Test that IODSpecBuilder.build_from_url calls progress_observer (Progress object)."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")

    progress_objects = []
    def observer(progress):
        progress_objects.append(progress)

    builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        progress_observer=observer
    )
    assert progress_objects  # Should be called at least once
    assert all(isinstance(p, Progress) for p in progress_objects)
    
    # Should see at least one high-level status
    high_level_statuses = {
        ProgressStatus.DOWNLOADING_IOD,
        ProgressStatus.PARSING_IOD_MODULE_LIST,
        ProgressStatus.PARSING_IOD_MODULES,
        ProgressStatus.SAVING_IOD_MODEL,
    }
    assert any(p.status in high_level_statuses for p in progress_objects)

    # Check for Step 1: DOWNLOADING_IOD events
    step1_events = [p for p in progress_objects if p.status == ProgressStatus.DOWNLOADING_IOD and p.step == 1]
    assert step1_events, "Should report progress for Step 1 (DOWNLOADING_IOD)"
    assert all(p.step == 1 for p in step1_events)
    assert all(p.status == ProgressStatus.DOWNLOADING_IOD for p in step1_events)

    # Check for Step 3: fine-grained PARSING_IOD_MODULES progress
    step3_events = [p for p in progress_objects if p.status == ProgressStatus.PARSING_IOD_MODULES and p.step == 3]
    assert step3_events, "Should report progress for Step 3 (PARSING_IOD_MODULES)"
    # Should see at least one percent update in step 3
    assert any(isinstance(p.percent, int) and 0 <= p.percent <= 100 for p in step3_events)
    assert all(p.step == 3 for p in step3_events)
    assert all(p.status == ProgressStatus.PARSING_IOD_MODULES for p in step3_events)

def test_iod_spec_builder_both_progress_callback_and_observer(monkeypatch):
    """Test that only progress_observer is called if both are provided."""
    factory = DummyFactory()
    factory.table_parser = factory
    factory.config = DummyConfig(cache_dir="cache")
    factory.model_store = DummyModelStore()
    builder = IODSpecBuilder(iod_factory=factory, module_factory=factory)
    monkeypatch.setattr(builder.dom_utils, "get_table_id_from_section", lambda dom, section_id: "table_PATIENT")

    progress_values = []
    def legacy_callback(percent):
        progress_values.append(percent)
    progress_objects = []
    def observer(progress):
        progress_objects.append(progress)

    builder.build_from_url(
        url="http://example.com",
        cache_file_name="file.xhtml",
        table_id="table_IOD",
        progress_callback=legacy_callback,
        progress_observer=observer
    )
    # Only the observer should be called, not the callback
    assert not progress_values
    assert progress_objects
    assert all(isinstance(p, Progress) for p in progress_objects)