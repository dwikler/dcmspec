"""Tests for the SpecPrinter class in dcmspec.spec_model."""
import logging
import pytest
from anytree import Node
from dcmspec.spec_model import SpecModel
from dcmspec.spec_printer import SpecPrinter

@pytest.fixture
def minimal_spec_model():
    """Create a minimal SpecModel with empty metadata and content nodes."""
    metadata = Node("metadata")
    metadata.header = []
    metadata.column_to_attr = {}
    content = Node("content")
    return SpecModel(metadata=metadata, content=content)

def add_standard_node(model, with_elem_tag=True):
    """Add a standard test node to the model's content tree and set typical metadata."""
    model.metadata.header = ["Name", "Tag"]
    model.metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    node = Node("element1", parent=model.content)
    setattr(node, "elem_name", "Element1")
    if with_elem_tag:
        setattr(node, "elem_tag", "(0101,0010)")
    return node

def test_init_sets_model_and_logger(minimal_spec_model):
    """Test that SpecPrinter initializes model and logger correctly."""
    model = minimal_spec_model
    printer = SpecPrinter(model)
    assert printer.model is model
    assert isinstance(printer.logger, logging.Logger)

def test_init_raises_typeerror_for_bad_logger(minimal_spec_model):
    """Test that SpecPrinter raises TypeError if logger is not a Logger instance."""
    model = minimal_spec_model
    with pytest.raises(TypeError):
        SpecPrinter(model, logger="not_a_logger")

def test_print_tree_does_not_crash(monkeypatch, minimal_spec_model):
    """Test that print_tree can be called without error."""
    model = minimal_spec_model
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_tree()

def test_print_tree_node_missing_attribute(monkeypatch, minimal_spec_model):
    """Test that print_tree handles nodes missing an attribute specified in attr_names."""
    model = minimal_spec_model
    add_standard_node(model, with_elem_tag=False)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # Should not raise, should print empty string for missing attribute
    printer.print_tree(attr_names=["elem_name", "elem_tag"])

def test_print_tree_attr_names_string_and_list(monkeypatch, minimal_spec_model):
    """Test that print_tree works with attr_names as a string and as a list."""
    model = minimal_spec_model
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # attr_names as string
    printer.print_tree(attr_names="elem_name")
    # attr_names as list
    printer.print_tree(attr_names=["elem_name", "elem_tag"])

def test_print_tree_attr_widths(monkeypatch, minimal_spec_model):
    """Test that print_tree applies attr_widths for padding/truncation."""
    model = minimal_spec_model
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # attr_widths: elem_name padded to 5, elem_tag padded to 2
    printer.print_tree(attr_names=["elem_name", "elem_tag"], attr_widths=[5, 2])

def test_print_tree_no_color(monkeypatch, minimal_spec_model):
    """Test that print_tree does not apply color styles when colorize=False."""
    model = minimal_spec_model
    add_standard_node(model)
    printer = SpecPrinter(model)
    styles = []
    
    # Patch printer.console.print to capture the style attribute of the Text object for each print call
    monkeypatch.setattr(
        printer.console,
        "print",
        lambda text, *args, **kwargs: styles.append(getattr(text, "style", None)),
    )

    printer.print_tree(colorize=False)
    # All styles should be "default" or None (Rich may use None for no style)
    assert all(s in ("default", None, "") for s in styles), f"Unexpected styles: {styles}"
    
def test_print_table_does_not_crash(monkeypatch, minimal_spec_model):
    """Test that print_table can be called without error."""
    model = minimal_spec_model
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_table()

def test_print_table_empty_header(monkeypatch, minimal_spec_model):
    """Test that print_table works when metadata.header is empty."""
    model = minimal_spec_model
    model.metadata.header = []  # Explicitly set header to empty for clarity
    model.metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_table()

def test_print_table_empty_column_to_attr(monkeypatch, minimal_spec_model):
    """Test that print_table works when metadata.column_to_attr is empty."""
    model = minimal_spec_model
    model.metadata.header = ["Name", "Tag"]
    model.metadata.column_to_attr = {}  # Explicitly set column_to_attr to empty for clarity
    add_standard_node(model)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_table()

def test_print_table_node_missing_attribute(monkeypatch, minimal_spec_model):
    """Test that print_table handles nodes missing an attribute defined in column_to_attr."""
    model = minimal_spec_model
    model.metadata.header = ["Name", "Tag"]
    model.metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    add_standard_node(model, with_elem_tag=False)
    printer = SpecPrinter(model)
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    # Should not raise, should print empty string for missing attribute
    printer.print_table()

def test_print_table_row_style(monkeypatch, minimal_spec_model):
    """Test that print_table sets the correct row style for include, title, and default nodes."""
    model = minimal_spec_model
    model.metadata.header = ["Name", "Tag"]
    model.metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}

    # Include node
    include_node = Node("include_table_macro", parent=model.content)
    setattr(include_node, "elem_name", "Include Table Macro")

    # Title node
    title_node = Node("title_node", parent=model.content)
    setattr(title_node, "elem_name", "Module Title")
    # Patch _is_title to return True for title_node only
    model._is_title = lambda node: node is title_node

    # Standard node
    add_standard_node(model)

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

def test_print_table_no_color(monkeypatch, minimal_spec_model):
    """Test that print_table sets style=None for all rows when colorize=False."""
    model = minimal_spec_model
    model.metadata.header = ["Name", "Tag"]
    model.metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    # Add two standard nodes with different tags
    add_standard_node(model)
    node2 = Node("element2", parent=model.content)
    setattr(node2, "elem_name", "Element2")
    setattr(node2, "elem_tag", "(0101,0020)")
    printer = SpecPrinter(model)
    # Patch Table.add_row to track calls
    styles = []
    monkeypatch.setattr("rich.table.Table.add_row", lambda *args, style=None, **kwargs: styles.append(style))
    monkeypatch.setattr(printer.console, "print", lambda *args, **kwargs: None)
    printer.print_table(colorize=False)
    # All add_row calls should have style=None
    assert all(s is None for s in styles)







