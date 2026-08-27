"""Tests for the ModuleRegistry class in dcmspec.module_registry."""
from dcmspec.module_registry import ModuleRegistry
from dcmspec.spec_model import SpecModel
from anytree import Node

def test_module_registry_basic_usage():
    """Test basic usage of ModuleRegistry: set, get, contains, keys, values, items."""
    registry = ModuleRegistry()
    model1 = SpecModel(metadata=Node("metadata1"), content=Node("content1"))
    model2 = SpecModel(metadata=Node("metadata2"), content=Node("content2"))

    # Test setitem and getitem
    registry["table_A"] = model1
    registry["table_B"] = model2
    assert registry["table_A"] is model1
    assert registry["table_B"] is model2

    # Test contains
    assert "table_A" in registry
    assert "table_B" in registry
    assert "table_C" not in registry

    # Test keys, values, items
    keys = set(registry.keys())
    assert keys == {"table_A", "table_B"}
    values = set(registry.values())
    assert values == {model1, model2}
    items = dict(registry.items())
    assert items == {"table_A": model1, "table_B": model2}