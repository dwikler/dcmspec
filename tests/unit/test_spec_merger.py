
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

def test_specmerger_add_missing_nodes_from_model(merge_by_path_test_models, merger):
    """Test that _add_missing_nodes_from_model adds nodes from model2 that are missing in model1."""
    current, other = merge_by_path_test_models

    # Add an extra top-level node to 'other'
    extra_node = Node("extra_element", parent=other.content)
    extra_node.elem_name = "Extra Element"
    extra_node.elem_tag = "(0101,1012)"
    extra_node.n_set = "1"

    # Act
    merged = merger.merge_path(current, other, attribute_name="elem_tag", merge_attrs=["n-set"])

    # Assert: the extra node from other should be present in the merged model
    found = next(
        (n for n in merged.content.descendants if getattr(n, "elem_tag", None) == "(0101,1012)"), None
    )
    assert found is not None
    assert getattr(found, "elem_name", None) == "Extra Element"
    assert getattr(found, "n_set", None) == "1"

def test_specmerger_add_missing_nodes_with_strip_module_level(merge_by_path_test_models_with_module, merger):
    """Test that _add_missing_nodes_from_model adds nodes from model2 to model1 when ignore_module_level is True."""
    current, other = merge_by_path_test_models_with_module

    # Add an extra node to 'other' that would only match if module level is ignored
    from anytree import Node
    extra_node = Node("extra_element", parent=other.content)
    extra_node.elem_name = "Extra Element"
    extra_node.elem_tag = "(0101,1012)"
    extra_node.dimse_nset = "1"
    extra_node.vr = "LO"

    # Act: ignore_module_level=True to trigger strip_module_level logic
    merged = merger.merge_path(
        current,
        other,
        attribute_name="elem_tag",
        merge_attrs=["dimse_nset", "vr"],
        ignore_module_level=True,
    )

    # Assert: the extra node from other should be present in the merged model
    found = next(
        n for n in merged.content.descendants if getattr(n, "elem_tag", None) == "(0101,1012)"
    )
    assert getattr(found, "elem_name", None) == "Extra Element"
    assert getattr(found, "dimse_nset", None) == "1"
    assert getattr(found, "vr", None) == "LO"

    # Assert: the extra node was added as a direct child of 'content' and not nested under a module node
    path_names = tuple(n.name for n in found.path)
    assert "my_module" not in path_names
    assert path_names[:2] == ("content", "extra_element")

def test_specmerger_merge_path_with_default_sets_elem_type(merge_by_path_test_models_with_missing_attr, merger):
    """Test merge_path_with_default sets default value '3' for missing elem_type after merging."""
    current, other = merge_by_path_test_models_with_missing_attr

    # Act
    merged = merger.merge_path_with_default(
        current,
        other,
        match_by="attribute",
        attribute_name="elem_tag",
        merge_attrs=["n-set"],
        default_attr="elem_type",
        default_value="3"
    )

    # Assert: top-level "my_element" should have elem_type "3" (from default)
    merged_first = next(child for child in merged.content.children if child.name == "my_element")
    assert getattr(merged_first, "elem_type") == "3"

    # Assert: "my_seq_element" should have elem_type "3" (from default)
    merged_parent = next(child for child in merged.content.children if child.name == "my_seq_element")
    assert getattr(merged_parent, "elem_type") == "3"

    # Assert: nested "my_element" under "my_seq_element" should have elem_type "3" (from default)
    merged_child = next(child for child in merged_parent.children if getattr(child, "elem_tag", None) == "(0101,1011)")
    assert getattr(merged_child, "elem_type") == "3"

def test_specmerger_merge_many_chained(mergemany_by_node_test_models, merger):
    """Test SpecMerger.merge_many merges more than two models in sequence."""
    # Arrange    
    current, second, third = mergemany_by_node_test_models

    merged = merger.merge_many(
        [current, second, third],
        method="matching_path",
        match_by="attribute",
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
        merger.merge_many([], method="matching_path", match_by="attribute", attribute_names=[], merge_attrs_list=[])

def test_specmerger_merge_many_mismatched_attribute_names(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError if attribute_names length is wrong."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many(
            [current, other],
            method="matching_path",
            match_by="attribute",
            attribute_names=["elem_tag", "extra"],
            merge_attrs_list=[["n-set"]],
        )

def test_specmerger_merge_many_mismatched_merge_attrs_list(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError if merge_attrs_list length is wrong."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many(
            [current, other],
            method="matching_path",
            match_by="attribute",
            attribute_names=["elem_tag"],
            merge_attrs_list=[["n-set"], ["extra"]],
        )

def test_specmerger_merge_many_unknown_method(merge_by_path_test_models, merger):
    """Test SpecMerger.merge_many raises ValueError for unknown method."""
    current, other = merge_by_path_test_models
    with pytest.raises(ValueError):
        merger.merge_many(
            [current, other],
            method="unknown",
            match_by="attribute",
            attribute_names=["elem_tag"],
            merge_attrs_list=[["n-set"]],
        )

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
        match_by="attribute",
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
            match_by="attribute",
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
        match_by="attribute",
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
        match_by="attribute",
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
        match_by="attribute",
        attribute_names=["elem_tag"],
        merge_attrs_list=[["n-set"]],
        json_file_name=json_file_name,
    )

    # Assert: cache should not be used if an extra attribute is present
    assert merged is not dummy_model_extra