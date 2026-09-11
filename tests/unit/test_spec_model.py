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
    # sourcery skip: extract-duplicate-method
    """Test that exclude_titles removes title nodes but not include nodes (attributes set to None if missing)."""
    metadata = Node("metadata")
    metadata.column_to_attr = {0: "elem_name", 1: "elem_tag"}
    content = Node("content")
    model = SpecModel(metadata=metadata, content=content)
    # Title node: only elem_name is set, elem_tag is None
    title_node = Node("module_title", parent=content)
    setattr(title_node, "elem_name", "Module Title")
    setattr(title_node, "elem_tag", None)
    # Non-title node: both attributes set
    non_title_node = Node("my_element", parent=content)
    setattr(non_title_node, "elem_name", "MyElement")
    setattr(non_title_node, "elem_tag", "(0101,0010)")
    # Include node: name contains "include_table"
    include_node = Node("include_table_macro", parent=content)
    setattr(include_node, "elem_name", "Include Table Macro")
    setattr(include_node, "elem_tag", None)
    # Run exclude_titles
    model.exclude_titles()
    children = list(model.content.children)
    assert non_title_node in children
    assert include_node in children
    assert title_node not in children


def test_exclude_titles_and_filter_required_no_nodes_removed():
    # sourcery skip: extract-duplicate-method
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

def assert_node_attrs(node: Node, expected: dict) -> None:
    """Assert that a node has all expected attributes with expected values (helper function)."""
    for k, v in expected.items():
        assert getattr(node, k) == v

def test_merge_matching_path_by_name(merge_by_path_test_models):
    """Test merge_matching_path merges attributes of nodes with matching node path."""
    # Arrange
    current, other = merge_by_path_test_models

    # Act
    merged = current.merge_matching_path(other, match_by="name", merge_attrs=["n-set"])

    # Assert
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"})

    # Assert
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"})

def test_merge_matching_path_by_attribute(merge_by_path_test_models):
    """Test merge_matching_path merges attributes of nodes with matching attribute path."""
    # Arrange
    current, other = merge_by_path_test_models

    # Act
    merged = current.merge_matching_path(other, match_by="attribute", attribute_name="elem_tag", merge_attrs=["n-set"])

    # Assert
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"})

def test_merge_matching_path_ignore_module_level(merge_by_path_test_models_with_module, capsys):
    """Test merge_matching_path with ignore_module_level=True merges nodes correctly across module level."""
    # Arrange
    current, other = merge_by_path_test_models_with_module

    # Act
    merged = current.merge_matching_path(
        other,
        match_by="attribute",
        attribute_name="elem_tag",
        merge_attrs=["dimse_nset", "vr"],
        ignore_module_level=True
    )

    # Assert
    # The merged model should have dimse_nset and vr attributes from 'other' on matching nodes, even though
    # current has a module level and other does not.
    # Check top-level element
    merged_top = next(child for child in merged.content.children[0].children if child.name == "my_element")
    assert getattr(merged_top, "elem_name") == "My Element"
    assert getattr(merged_top, "elem_tag") == "(0010,0010)"
    assert getattr(merged_top, "dimse_nset") == "2"
    assert getattr(merged_top, "vr") == "PN"
    # Check sequence element
    merged_seq = next(child for child in merged.content.children[0].children if child.name == "my_seq_element")
    assert getattr(merged_seq, "elem_name") == "My Element Sequence"
    assert getattr(merged_seq, "elem_tag") == "(0010,0020)"
    assert getattr(merged_seq, "dimse_nset") == "1"
    assert getattr(merged_seq, "vr") == "SQ"
    # Check nested element
    merged_nested = next(child for child in merged_seq.children if child.name == ">my_element")
    assert getattr(merged_nested, "elem_name") == "My Element"
    assert getattr(merged_nested, "elem_tag") == "(0010,0010)"
    assert getattr(merged_nested, "dimse_nset") == "3"
    assert getattr(merged_nested, "vr") == "PN"
    
def test_merge_matching_path_by_attribute_different_path_no_merge(merge_test_models_different_path):
    """Test merge_matching_path does not merge nodes if attribute path differs at any level."""
    # Arrange
    current, other = merge_test_models_different_path

    # Act
    merged = current.merge_matching_path(other, match_by="attribute", attribute_name="elem_tag", merge_attrs=["n-set"])

    # Assert
    merged_parent = next(
        child for child in merged.content.children
        if getattr(child, "elem_tag", None) == "(0101,1010)"
    )
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)"})

def test_merge_matching_path_invalid_match_by_raises(merge_test_models_different_path):
    """Test merge_matching_path raises ValueError for invalid match_by argument."""
    # Arrange
    current, other = merge_test_models_different_path

    # Act & Assert
    with pytest.raises(ValueError):
        current.merge_matching_path(other, match_by="invalid")

def test_merge_matching_node_by_name_node_match(merge_by_node_test_models):
    """Test merge_matching_node merges attributes of nodes with matching node name (node match)."""
    # Arrange
    current, other = merge_by_node_test_models

    # Act
    merged = current.merge_matching_node(other, match_by="name", merge_attrs=["vr"])

    # Assert
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "vr": "CS"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})

def test_merge_matching_node_by_attribute_node_match(merge_by_node_test_models):
    """Test merge_matching_node merges attributes of nodes with matching attribute value (node match)."""
    # Arrange
    current, other = merge_by_node_test_models

    # Act
    merged = current.merge_matching_node(other, match_by="attribute", attribute_name="elem_tag", merge_attrs=["vr"])

    # Assert
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "vr": "CS"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})

def test_merge_matching_node_by_attribute_no_merge_node_match(merge_test_models_different_path):
    """Test merge_matching_node does not merge attributes if attribute value does not match (node match)."""
    # Arrange
    current, other = merge_test_models_different_path

    # Act
    merged = current.merge_matching_node(other, match_by="attribute", attribute_name="elem_tag", merge_attrs=["vr"])

    # Assert
    merged_parent = next(
        child for child in merged.content.children
        if getattr(child, "elem_tag", None) == "(0101,1010)"
    )
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)"})

def test_merge_matching_node_invalid_match_by_raises_node_match(merge_by_node_test_models):
    """Test merge_matching_node raises ValueError for invalid match_by argument (node match)."""
    # Arrange
    current, other = merge_by_node_test_models

    # Act & Assert
    with pytest.raises(ValueError):
        current.merge_matching_node(other, match_by="invalid")
