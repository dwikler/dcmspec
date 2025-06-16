"""Shared pytest fixtures for the dcmspec test suite."""

from anytree import Node
import pytest

from dcmspec.spec_model import SpecModel

@pytest.fixture(autouse=True)
def patch_dirs(monkeypatch, tmp_path):
    """Patch platformdirs' user_cache_dir and user_config_dir to use unique temporary directories for each test."""
    cache_dir = tmp_path / "cache"
    config_dir = tmp_path / "config"
    monkeypatch.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    monkeypatch.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    # print(f"Test temp directory {tmp_path}")  # Uncomment for debugging with pytest -s
    return tmp_path


def make_spec_model_with_seq(
    top_attrs: dict,
    seq_attrs: dict,
    nested_attrs: dict = None,
    metadata_attrs: dict = None,
) -> SpecModel:
    """Create a SpecModel with a sequence.

    - a top-level node ("my_element") under content,
    - a node ("my_seq_element") under content,
    - optionally, a nested node ("my_element") under "my_seq_element" if nested_attrs is provided.
    - metadata_attrs: dict of attributes to set on the metadata node (e.g., header, column_to_attr)
    """
    metadata = Node("metadata")
    if metadata_attrs:
        for k, v in metadata_attrs.items():
            setattr(metadata, k, v)
    content = Node("content")
    # Top-level node
    top_node = Node("my_element", parent=content)
    for k, v in top_attrs.items():
        setattr(top_node, k, v)
    # Sequence node
    seq_node = Node("my_seq_element", parent=content)
    for k, v in seq_attrs.items():
        setattr(seq_node, k, v)
    # Add nested node under sequence
    if nested_attrs is not None:
        # Simulate Part 3 parsing: nested node name has leading '>'
        nested_node = Node(">my_element", parent=seq_node)
        for k, v in nested_attrs.items():
            setattr(nested_node, k, v)

    return SpecModel(metadata=metadata, content=content)

@pytest.fixture
def merge_by_path_test_models():
    """Create current and other SpecModel for merge_matching_path tests."""
    metadata_attrs = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_attrs,
    )
    metadata_attrs = {
        "header": ["Element Name", "Tag", "N-SET"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "n-set"},
    }
    other = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
        metadata_attrs=metadata_attrs,
    )
    return current, other

@pytest.fixture
def merge_by_node_test_models():
    """Create current and other SpecModel for merge_matching_node tests."""
    metadata_attrs = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_attrs,
    )
    metadata_attrs = {
        "header": ["Element Name", "Tag", "VR"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "vr"},
    }
    other = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "vr": "CS"},
        metadata_attrs=metadata_attrs,
    )
    return current, other

@pytest.fixture
def merge_test_models_different_path():
    """Create current and other SpecModel for merge_matching_path tests."""
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
    )
    other = make_spec_model_with_seq(
        {"elem_name": "Different", "elem_tag": "DIFFERENT", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
    )
    return current, other

@pytest.fixture
def mergemany_by_node_test_models():
    """Create current and other SpecModel for merge_matching_node tests."""
    metadata_attrs = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_attrs
    )
    metadata_attrs = {
        "header": ["Element Name", "Tag", "N-SET"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "n-set"},
    }    
    second = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
        metadata_attrs=metadata_attrs
    )
    third = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "R+"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "R+*"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "O"},
        metadata_attrs=metadata_attrs
    )
    return current, second, third
