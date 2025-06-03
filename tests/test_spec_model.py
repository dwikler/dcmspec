"""Tests for the SpecModel class in dcmspec.spec_model."""
import logging
import pytest
from anytree import Node
from dcmspec.spec_model import SpecModel

@pytest.fixture
def simple_spec_model():
    """Create a simple SpecModel with metadata and content nodes for testing."""
    metadata = Node("metadata")
    # Simulate column_to_attr for _is_title logic
    metadata.column_to_attr = {0: "title"}
    content = Node("content")
    return SpecModel(metadata=metadata, content=content)

def test_init_sets_metadata_and_content_and_logger(simple_spec_model):
    """Test that SpecModel initializes metadata, content, and logger."""
    model = simple_spec_model
    assert model.metadata.name == "metadata"
    assert model.content.name == "content"
    assert isinstance(model.logger, logging.Logger)

def test_exclude_titles_removes_title_and_skips_include_nodes():
    """Test that exclude_titles removes title nodes but not include nodes."""
    metadata = Node("metadata")
    # Setup column_to_attr so that key 0 is "elem_name" and key 1 is "elem_tag"
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    # This node should be considered a title (only has "elem_name" attribute)
    title_node = Node("module_title", parent=content)
    setattr(title_node, "elem_name", "Module Title")
    # This node should NOT be considered a title (has both "elem_name" and "elem_tag" attributes)
    non_title_node = Node("my_element", parent=content)
    setattr(non_title_node, "elem_name", "MyElement")
    setattr(non_title_node, "elem_tag", "(0101,0010)")
    # This node should be considered an include (name contains "include_table")
    include_node = Node("include_table_macro", parent=content)
    setattr(include_node, "elem_name", "Include Table Macro")
    # Run exclude_titles
    model.exclude_titles()
    children = list(model.content.children)
    assert non_title_node in children
    assert include_node in children
    assert title_node not in children

def test_exclude_titles_and_filter_required_no_nodes_removed():
    """Test that exclude_titles and filter_required do not remove any nodes if all are required and not titles."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_type"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    node1 = Node("element1", parent=content)
    setattr(node1, "elem_name", "Element1")
    setattr(node1, "elem_type", "1")
    node2 = Node("element2", parent=content)
    setattr(node2, "elem_name", "Element2")
    setattr(node2, "elem_type", "2")
    # Both nodes are required and have both attributes, so neither is a title
    model.exclude_titles()
    model.filter_required("elem_type")
    children = list(model.content.children)
    assert node1 in children
    assert node2 in children

def test_filter_required_removes_optional_nodes():
    """Test that filter_required removes nodes with type '3' and keeps required nodes."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_type"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    required_node = Node("required", parent=content)
    setattr(required_node, "elem_type", "1")
    optional_node = Node("optional", parent=content)
    setattr(optional_node, "elem_type", "3")
    model.filter_required("elem_type")
    children = list(model.content.children)
    assert required_node in children
    assert optional_node not in children

def test_filter_required_removes_sequence_node_and_descendants_type_3():
    """Test that filter_required removes a sequence node and its descendants if type is '3'."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_type"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    seq_node_3 = Node("seq3_sequence", parent=content)
    setattr(seq_node_3, "elem_type", "3")
    child_3 = Node("child3", parent=seq_node_3)
    model.filter_required("elem_type")
    assert seq_node_3.parent is None
    assert child_3.parent is None

def test_filter_required_removes_only_descendants_type_2():
    """Test that filter_required removes only descendants of a sequence node if type is '2'."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_type"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    seq_node_2 = Node("seq2_sequence", parent=content)
    setattr(seq_node_2, "elem_type", "2")
    child_2 = Node("child2", parent=seq_node_2)
    model.filter_required("elem_type")
    assert seq_node_2.parent == content
    assert child_2.parent is None

def test_filter_required_custom_keep_remove():
    """Test that filter_required respects custom keep and remove arguments."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_type"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    node_a = Node("a", parent=content)
    setattr(node_a, "elem_type", "R")
    node_b = Node("b", parent=content)
    setattr(node_b, "elem_type", "O")
    node_c = Node("c", parent=content)
    setattr(node_c, "elem_type", "X")
    # Only keep "X", remove "Y" and "Z"
    model.filter_required("elem_type", keep=["R"], remove=["O", "X"])
    children = list(model.content.children)
    assert node_a in children
    assert node_b not in children
    assert node_c not in children



