"""Tests for the SectionRegistry class in dcmspec.section_registry."""
from dcmspec.section_registry import SectionRegistry
from dcmspec.spec_model import SpecModel
from anytree import Node

def test_section_registry_basic_usage():
    """Test basic usage of SectionRegistry: set, get, contains, keys, values, items."""
    registry = SectionRegistry()
    model1 = SpecModel(metadata=Node("metadata1"), content=Node("content1"))
    model2 = SpecModel(metadata=Node("metadata2"), content=Node("content2"))

    # Test setitem and getitem
    registry["sect_A"] = model1
    registry["sect_B"] = model2
    assert registry["sect_A"] is model1
    assert registry["sect_B"] is model2

    # Test contains
    assert "sect_A" in registry
    assert "sect_B" in registry
    assert "sect_C" not in registry

    # Test keys, values, items
    keys = set(registry.keys())
    assert keys == {"sect_A", "sect_B"}
    values = set(registry.values())
    assert values == {model1, model2}
    items = dict(registry.items())
    assert items == {"sect_A": model1, "sect_B": model2}
