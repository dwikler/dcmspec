
"""Tests for the SpecMerger class in dcmspec.spec_merger.

This module provides tests for the SpecMerger class, which merges DICOM specification models
using both path-based and node-based strategies. The tests verify that merging works as expected
for both strategies, including cases where nodes with the same attribute value appear at different
levels in the tree.
"""
from anytree import Node
import pytest
from pathlib import Path
from dcmspec.spec_merger import SpecMerger

@pytest.fixture
def merger(patch_dirs):
    """Fixture to provide a SpecMerger instance with a patched cache dir."""
    return SpecMerger(config=None, model_store=None, logger=None)

def assert_node_attrs(node: Node, expected: dict) -> None:
    """Assert that a node has all expected attributes with expected values (helper function)."""
    for k, v in expected.items():
        assert getattr(node, k) == v

def test_specmerger_merge_node(merge_by_node_test_models, merger):
    """Test SpecMerger.merge_node merges all nodes with matching attribute value, regardless of path.

    This test verifies that node-based merging applies the merged attribute to all nodes
    with the same attribute value (here, 'elem_tag'), even if they are at different levels in the tree.
    """
    # Arrange
    current, other = merge_by_node_test_models

    # Act
    merged = merger.merge_node(current, other, match_by="attribute", attribute_name="elem_tag", merge_attrs=["vr"])

    # Assert: top-level and nested "my_element" should get the same "vr" value from other
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "vr": "CS"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"})

    # Assert: metadata includes all expected attributes (original + merged)
    expected_attrs = ["elem_name", "elem_tag", "vr"]
    # Robustly handle int/str keys in column_to_attr
    col2attr = merged.metadata.column_to_attr
    # Convert all keys to int for sorting, but keep the original key for lookup
    sorted_items = sorted(
        col2attr.items(), 
        key=lambda item: int(item[0]) if isinstance(item[0], (int, str)) and str(item[0]).isdigit() else float('inf'))
    actual_attrs = [v for k, v in sorted_items]
    assert actual_attrs == expected_attrs
    # Also check that the header includes the new column
    assert any("vr" in h.lower() for h in merged.metadata.header)

def test_specmerger_merge_path(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_path merges only nodes with matching attribute path.

    This test verifies that path-based merging applies the merged attribute only to nodes
    whose full path (including all ancestors) matches between the two models.
    """
    # Arrange    
    current, other = merge_by_path_test_models

    # Act
    merged = merger.merge_path(current, other, attribute_name="elem_tag", merge_attrs=["n-set"])

    # Assert: top-level and nested "my_element" should get different "n-set" value from other
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert_node_attrs(merged_first, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"})
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert_node_attrs(merged_parent, {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"})
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert_node_attrs(merged_child, {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"})
    
    # Assert: metadata includes all expected attributes (original + merged)
    expected_attrs = ["elem_name", "elem_tag", "n-set"]
    col2attr = merged.metadata.column_to_attr
    # Convert all keys to int for sorting, but keep the original key for lookup
    sorted_items = sorted(
        col2attr.items(),
        key=lambda item: int(item[0]) if isinstance(item[0], (int, str)) and str(item[0]).isdigit() else float('inf')
    )
    actual_attrs = [v for k, v in sorted_items]
    assert actual_attrs == expected_attrs
    # Also check that the header includes the new column
    assert any("n-set" in h.lower() for h in merged.metadata.header)

def test_specmerger_merge_many_chained(mergemany_by_node_test_models, merger):
    """Test SpecMerger.merge_many merges more than two models in sequence."""
    # Arrange    
    current, second, third = mergemany_by_node_test_models

    merged = merger.merge_many(
        [current, second, third],
        method="matching_path",
        attribute_names=[ "elem_tag", "elem_tag" ],
        merge_attrs_list=[ ["n-set"], ["n-set"] ]
    )
    # Assert: values from third model should be present
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert getattr(merged_first, "n-set") == "R+"
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert getattr(merged_parent, "n-set") == "R+*"
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert getattr(merged_child, "n-set") == "O"

    # Assert: metadata includes all expected attributes (original + merged)
    expected_attrs = ["elem_name", "elem_tag", "n-set"]
    col2attr = merged.metadata.column_to_attr
    # Convert all keys to int for sorting, but keep the original key for lookup
    sorted_items = sorted(
        col2attr.items(),
        key=lambda item: int(item[0]) if isinstance(item[0], (int, str)) and str(item[0]).isdigit() else float('inf')
    )
    actual_attrs = [v for k, v in sorted_items]
    assert actual_attrs == expected_attrs
    # Also check that the header includes the new column
    assert any("n-set" in h.lower() for h in merged.metadata.header)

def test_specmerger_merge_many_empty(merger):
    """Test SpecMerger.merge_many raises ValueError if models is empty."""
    with pytest.raises(ValueError):
        merger.merge_many([])

def test_specmerger_merge_many_mismatched_attribute_names(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError if attribute_names length is wrong."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many([current, other], method="matching_path", attribute_names=["elem_tag", "extra"])

def test_specmerger_merge_many_mismatched_merge_attrs_list(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError if merge_attrs_list length is wrong."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many([current, other], method="matching_path", merge_attrs_list=[["n-set"], ["extra"]])

def test_specmerger_merge_many_unknown_method(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError for unknown method."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many([current, other], method="unknown")

def test_specmerger_merge_node_and_path_defaults(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_node and merge_path with default attribute_name and merge_attrs."""
    current, other = merge_by_path_test_models
    # Should not raise or fail, just not merge any new attributes
    merged_node = merger.merge_node(current, other)
    merged_path = merger.merge_path(current, other)
    # The structure should be preserved
    assert any(child.name == "my_element" for child in merged_node.content.children)
    assert any(child.name == "my_seq_element" for child in merged_path.content.children)


def test_specmerger_merge_many_saves_cache(
    merge_by_path_test_models, merger, patch_dirs, monkeypatch
):
    """Test that merge_many saves cache file when json_file_name is present and force_update is not set."""
    # Arrange    
    current, other = merge_by_path_test_models

    # Patch the save method of the model_store instance to capture its arguments
    saved = {}

    def fake_save(model, path):
        saved["model"] = model
        saved["path"] = path

    monkeypatch.setattr(merger.model_store, "save", fake_save)

    # Act
    json_file_name = "test_merged.json"
    merged = merger.merge_many(
        [current, other],
        method="matching_path",
        attribute_names=["elem_tag"],
        merge_attrs_list=[["n-set"]],
        json_file_name=json_file_name,
    )

    # Assert path to saved json file and call to SpecStore save method
    expected_path = str(Path(patch_dirs) / "cache" / "model" / json_file_name)
    assert saved["path"] == expected_path
    assert saved["model"] is merged


def test_specmerger_merge_many_save_failure_logs_warning(
    merge_by_path_test_models, merger, patch_dirs, monkeypatch, caplog
):
    """Test that merge_many logs a warning if saving the cache file fails."""
    # Arrange    
    current, other = merge_by_path_test_models

    # Patch the save method of the model_store instance to simulate failure
    def fail_save(model, path):
        raise IOError("Simulated save failure")

    monkeypatch.setattr(merger.model_store, "save", fail_save)

    # Act
    json_file_name = "fail_merged.json"
    with caplog.at_level("WARNING"):
        merger.merge_many(
            [current, other],
            method="matching_path",
            attribute_names=["elem_tag"],
            merge_attrs_list=[["n-set"]],
            json_file_name=json_file_name,
        )

    # Assert log warning message
    assert any(
        "Failed to cache merged model" in record.message and "Simulated save failure" in record.message
        for record in caplog.records
    )

class DummyModel:
    """Minimal stand-in for SpecModel for cache validation tests.

    This dummy model mimics the minimal interface of a SpecModel required for cache tests:
    it has a .metadata attribute, which is an anytree Node with a .column_to_attr attribute.
    """

    def __init__(self, attrs):
        """Initialize DummyModel with a metadata node.

        Args:
            attrs (dict): The column_to_attr mapping to set on the metadata node.

        """
        self.metadata = Node("metadata")
        self.metadata.column_to_attr = attrs

def test_specmerger_merge_many_loads_cache_valid(
    merge_by_path_test_models, merger, patch_dirs, monkeypatch
):
    """Test that merge_many loads the merged model from cache if present, valid, and force_update is False."""
    # Arrange    
    current, other = merge_by_path_test_models

    # Patch model_store load to simulate all requested attributes present, no extra attributes
    dummy_model_valid = DummyModel({0: "elem_name", 1: "elem_tag", 2: "n-set"})

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr(merger.model_store, "load", lambda path: dummy_model_valid)

    # Act
    json_file_name = "cached_merged.json"
    merged = merger.merge_many(
        [current, other],
        method="matching_path",
        attribute_names=["elem_tag"],
        merge_attrs_list=[["n-set"]],
        json_file_name=json_file_name,
    )

    # Assert cache is used
    assert merged is dummy_model_valid

def test_specmerger_merge_many_loads_cache_missing_attr(
    merge_by_path_test_models, merger, patch_dirs, monkeypatch
):
    """Test that merge_many does not use cache if a requested attribute is missing."""
    # Arrange    
    current, other = merge_by_path_test_models

    # Patch model_store load to simulate missing requested attribute
    dummy_model_missing = DummyModel({0: "elem_name", 1: "elem_tag"})

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr(merger.model_store, "load", lambda path: dummy_model_missing)
    json_file_name = "cached_merged.json"
    merged = merger.merge_many(
        [current, other],
        method="matching_path",
        attribute_names=["elem_tag"],
        merge_attrs_list=[["n-set"]],
        json_file_name=json_file_name,
    )

    # Assert: cache should not be used if a requested attribute is missing
    assert merged is not dummy_model_missing

def test_specmerger_merge_many_loads_cache_extra_attr(
    merge_by_path_test_models, merger, patch_dirs, monkeypatch
):
    """Test that merge_many does not use cache if there is an extra attribute not in original or requested."""
    # Arrange    
    current, other = merge_by_path_test_models

    # Patch model_store load to simulate extra attribute present
    dummy_model_extra = DummyModel({0: "elem_name", 1: "elem_tag", 2: "n-set", 3: "extra"})

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr(merger.model_store, "load", lambda path: dummy_model_extra)
    json_file_name = "cached_merged.json"
    merged = merger.merge_many(
        [current, other],
        method="matching_path",
        attribute_names=["elem_tag"],
        merge_attrs_list=[["n-set"]],
        json_file_name=json_file_name,
    )

    # Assert: cache should not be used if an extra attribute is present
    assert merged is not dummy_model_extra