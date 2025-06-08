"""Tests for the IODSpecPrinter class in dcmspec.iod_spec_printer."""
import pytest
from anytree import Node
from rich.console import Console
from dcmspec.iod_spec_printer import IODSpecPrinter
from dcmspec.spec_model import SpecModel

@pytest.fixture
def iod_spec_model():
    """Fixture for a minimal IOD SpecModel with a module and attribute node."""
    metadata = Node("metadata")
    metadata.header = ["Attr1", "Attr2"]
    metadata.column_to_attr = {0: "attr1", 1: "attr2"}
    content = Node("content")
    # Add a module node
    module_node = Node("module1", parent=content)
    setattr(module_node, "module", "Patient")
    setattr(module_node, "usage", "M")
    # Add an attribute node under the module node
    attr_node = Node("attr", parent=module_node)
    setattr(attr_node, "attr1", "Value1")
    setattr(attr_node, "attr2", "Value2")
    # Add helpers for color logic
    model = SpecModel(metadata=metadata, content=content)
    model._is_include = lambda node: False
    model._is_title = lambda node: False
    return model

def test_print_table_prints_module_title_and_attr(iod_spec_model):
    """Test that module title and attribute values are present in the output."""
    printer = IODSpecPrinter(iod_spec_model)
    with printer.console.capture() as capture:
        printer.print_table(colorize=False)
    result = capture.get()
    assert "Patient Module (M)" in result
    assert "Value1" in result
    assert "Value2" in result