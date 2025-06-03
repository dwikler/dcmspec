"""Tests for the SpecPrinter class in dcmspec.spec_model."""
import logging
import pytest
from anytree import Node
from dcmspec.spec_model import SpecModel
from dcmspec.spec_printer import SpecPrinter

def test_init_sets_model_and_logger():
    """Test that SpecPrinter initializes model and logger correctly."""
    metadata = Node("metadata")
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    printer = SpecPrinter(model)
    assert printer.model is model
    assert isinstance(printer.logger, logging.Logger)

def test_init_raises_typeerror_for_bad_logger():
    """Test that SpecPrinter raises TypeError if logger is not a Logger instance."""
    metadata = Node("metadata")
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    with pytest.raises(TypeError):
        SpecPrinter(model, logger="not_a_logger")

def test_print_tree_does_not_crash(monkeypatch):
    """Test that print_tree can be called without error."""
    metadata = Node("metadata")
    metadata.header = ["Name", "Tag"]
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    node = Node("element1", parent=content)
    setattr(node, "elem_name", "Element1")
    setattr(node, "elem_tag", "(0101,0010)")
    model = SpecModel(metadata=metadata, content=content)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_tree()

def test_print_tree_attr_names_string_and_list(monkeypatch):
    """Test that print_tree works with attr_names as a string and as a list."""
    metadata = Node("metadata")
    metadata.header = ["Name", "Tag"]
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    node = Node("element1", parent=content)
    setattr(node, "elem_name", "Element1")
    setattr(node, "elem_tag", "(0101,0010)")
    model = SpecModel(metadata=metadata, content=content)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # attr_names as string
    printer.print_tree(attr_names="elem_name")
    # attr_names as list
    printer.print_tree(attr_names=["elem_name", "elem_tag"])

def test_print_tree_attr_widths(monkeypatch):
    """Test that print_tree applies attr_widths for padding/truncation."""
    metadata = Node("metadata")
    metadata.header = ["Name", "Tag"]
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    node = Node("element1", parent=content)
    setattr(node, "elem_name", "E1")
    setattr(node, "elem_tag", "T")
    model = SpecModel(metadata=metadata, content=content)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # attr_widths: elem_name padded to 5, elem_tag padded to 2
    printer.print_tree(attr_names=["elem_name", "elem_tag"], attr_widths=[5, 2])

def test_print_table_does_not_crash(monkeypatch):
    """Test that print_table can be called without error."""
    metadata = Node("metadata")
    metadata.header = ["Name", "Tag"]
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    node = Node("element1", parent=content)
    setattr(node, "elem_name", "Element1")
    setattr(node, "elem_tag", "(0101,0010)")
    model = SpecModel(metadata=metadata, content=content)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_table()
    
def test_print_table_row_style(monkeypatch):
    """Test that print_table sets the correct row style for include, title, and default nodes."""
    metadata = Node("metadata")
    metadata.header = ["Name", "Tag"]
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)

    # Include node
    include_node = Node("include_table_macro", parent=content)
    setattr(include_node, "elem_name", "Include Table Macro")

    # Title node
    title_node = Node("title_node", parent=content)
    setattr(title_node, "elem_name", "Module Title")
    # Patch _is_title to return True for title_node only
    model._is_title = lambda node: node is title_node

    # Default node
    default_node = Node("regular", parent=content)
    setattr(default_node, "elem_name", "My Element")
    setattr(default_node, "elem_tag", "(0101,0010)")

    printer = SpecPrinter(model)

    # Capture the styles passed to add_row
    styles = []

    # Patch Table.add_row
    monkeypatch.setattr("rich.table.Table.add_row", lambda *args, style=None, **kwargs: styles.append(style))
    # Patch console.print to avoid output
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)

    printer.print_table(colorize=True)

    # The order is: include_node, title_node, default_node (since PreOrderIter)
    assert "yellow" in styles
    assert "magenta" in styles
    assert any(
        s in styles
        for s in [
            "rgb(255,255,255)",
            "rgb(173,216,230)",
            "rgb(135,206,250)",
            "rgb(0,191,255)",
            "rgb(30,144,255)",
            "rgb(0,0,255)",
        ]
    )