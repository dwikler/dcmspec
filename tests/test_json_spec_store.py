"""Tests for the JSONSpecStore class in dcmspec.json_spec_store."""
import os
import pytest
from unittest.mock import patch
from anytree import Node
from anytree.exporter import JsonExporter

from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.spec_model import SpecModel

@pytest.fixture
def simple_spec_model(tmp_path):
    """Create a simple SpecModel with metadata and content nodes for testing."""
    metadata = Node("metadata")
    content = Node("content")
    return SpecModel(metadata=metadata, content=content)

def test_save_and_load_roundtrip(tmp_path, simple_spec_model):
    """Test that JSONSpecStore.save and load work as a roundtrip for a simple SpecModel."""
    store = JSONSpecStore()
    json_path = tmp_path / "model.json"
    store.save(simple_spec_model, str(json_path))
    loaded_model = store.load(str(json_path))
    assert isinstance(loaded_model, SpecModel)
    assert loaded_model.metadata.name == "metadata"
    assert loaded_model.content.name == "content"

def test_save_creates_directory(tmp_path, simple_spec_model):
    """Test that save creates the destination directory if it does not exist."""
    store = JSONSpecStore()
    model_dir = tmp_path / "dcmspec" / "model"
    json_path = model_dir / "model.json"
    store.save(simple_spec_model, str(json_path))
    assert os.path.exists(json_path)

def test_load_raises_on_missing_file(tmp_path):
    """Test that load raises RuntimeError if the file does not exist."""
    store = JSONSpecStore()
    missing_path = tmp_path / "does_not_exist.json"
    with pytest.raises(RuntimeError):
        store.load(str(missing_path))

def test_load_raises_on_invalid_json(tmp_path):
    """Test that load raises RuntimeError if the file is not valid JSON."""
    store = JSONSpecStore()
    bad_path = tmp_path / "bad.json"
    with open(bad_path, "w", encoding="utf-8") as f:
        f.write("{not: valid json}")
    with pytest.raises(RuntimeError):
        store.load(str(bad_path))

def test_save_raises_on_write_error(tmp_path, simple_spec_model):
    """Test that save raises RuntimeError if writing the file fails."""
    store = JSONSpecStore()
    json_path = tmp_path / "model.json"

    # Patch buitins.open only for save call
    with patch("builtins.open", side_effect=OSError("write error")):
        with pytest.raises(RuntimeError, match="Failed to write JSON file"):
            store.save(simple_spec_model, str(json_path))

def test_load_converts_column_to_attr_keys_to_int(tmp_path):
    """Test that load converts column_to_attr keys to int if present in metadata."""
    store = JSONSpecStore()
    # Create a minimal JSON structure with metadata.column_to_attr keys as strings
    from anytree import Node
    root = Node("dcmspec")
    metadata = Node("metadata", parent=root)
    Node("content", parent=root)
    # Simulate column_to_attr with string keys
    metadata.column_to_attr = {"0": "elem_name", "1": "elem_tag"}

    # Export to JSON
    exporter = JsonExporter(indent=4, sort_keys=False)
    json_path = tmp_path / "model.json"
    with open(json_path, "w", encoding="utf-8") as f:
        exporter.write(root, f)

    # Now load using JSONSpecStore and check that keys are ints
    loaded_model = store.load(str(json_path))
    assert isinstance(loaded_model, SpecModel)
    assert hasattr(loaded_model.metadata, "column_to_attr")
    assert all(isinstance(k, int) for k in loaded_model.metadata.column_to_attr.keys())
    assert loaded_model.metadata.column_to_attr[0] == "elem_name"
    assert loaded_model.metadata.column_to_attr[1] == "elem_tag"