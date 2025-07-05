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
    module_name: str = None,
) -> SpecModel:
    """Create a SpecModel with a sequence.

    - a top-level node ("my_element") under content,
    - a node ("my_seq_element") under content,
    - optionally, a nested node ("my_element") under "my_seq_element" if nested_attrs is provided.
    - If module_name is provided, all nodes are nested under a module node named as a snake_case version of module_name,
      and the "module" attribute is set to the original module_name string.
    - metadata_attrs: dict of attributes to set on the metadata node (e.g., header, column_to_attr)
    """
    import re

    def to_snake_case(name: str) -> str:
        # Convert "My Module" -> "my_module"
        return re.sub(r'\W+', '_', name).strip('_').lower()

    metadata = Node("metadata")
    if metadata_attrs:
        for k, v in metadata_attrs.items():
            setattr(metadata, k, v)
    content = Node("content")
    if module_name:
        module_node = Node(to_snake_case(module_name), parent=content)
        setattr(module_node, "module", module_name)
        parent = module_node
    else:
        parent = content
    # Top-level node
    top_node = Node("my_element", parent=parent)
    for k, v in top_attrs.items():
        setattr(top_node, k, v)
    # Sequence node
    seq_node = Node("my_seq_element", parent=parent)
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
    metadata_current = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_current,
    )
    metadata_other = {
        "header": ["Element Name", "Tag", "N-SET"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "n-set"},
    }
    other = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
        metadata_attrs=metadata_other,
    )
    return current, other

@pytest.fixture
def merge_by_path_test_models_with_module():
    """Create current and other SpecModel fixtures for UPS merge_matching_path tests.

    - current: module-level model (content -> my_module -> element/sequence/nested)
    - other: realistic UPSattributes-like model (content -> element, sequence, nested)
    """
    # Model 1: current (with module level)
    metadata_current = {
        "header": ["Module", "Element Name", "Tag", "Type"],
        "column_to_attr": {0: "module", 1: "elem_name", 2: "elem_tag", 3: "elem_type"},
    }
    current = make_spec_model_with_seq(
        top_attrs={"module": "My Module", "elem_name": "My Element", "elem_tag": "(0010,0010)", "elem_type": "1"},
        seq_attrs={
            "module": "My Module", "elem_name": "My Element Sequence", "elem_tag": "(0010,0020)", "elem_type": "2"
            },
        nested_attrs={
            "module": "My Module", "elem_name": "My Element", "elem_tag": "(0010,0010)", "elem_type": "3"
            },
        metadata_attrs=metadata_current,
        module_name="My Module"
    )

    # Model 2: other 
    metadata_other = {
        "header": ["Element Name", "Tag", "N-SET", "VR"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "dimse_nset", 3: "vr"},
    }
    other = make_spec_model_with_seq(
        top_attrs={"elem_name": "My Element", "elem_tag": "(0010,0010)", "dimse_nset": "2", "vr": "PN"},
        seq_attrs={"elem_name": "My Element Sequence", "elem_tag": "(0010,0020)", "dimse_nset": "1", "vr": "SQ"},
        nested_attrs={"elem_name": "My Element", "elem_tag": "(0010,0010)", "dimse_nset": "3", "vr": "PN"},
        metadata_attrs=metadata_other
    )

    return current, other

@pytest.fixture
def merge_by_path_test_models_with_missing_attr():
    """Create current and other SpecModel for merge_matching_path tests."""
    metadata_current = {
        "header": ["Element Name", "Tag", "Type"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_current,
    )
    metadata_other = {
        "header": ["Element Name", "Tag", "N-SET"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "n-set"},
    }
    other = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
        metadata_attrs=metadata_other,
    )
    return current, other

@pytest.fixture
def merge_by_node_test_models():
    """Create current and other SpecModel for merge_matching_node tests."""
    metadata_current = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_current,
    )
    metadata_other = {
        "header": ["Element Name", "Tag", "VR"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "vr"},
    }
    other = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "vr": "DS"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "vr": "CS"},
        metadata_attrs=metadata_other,
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
    metadata_current = {
        "header": ["Element Name", "Tag"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag"},
    }
    current = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)"},
        metadata_attrs=metadata_current
    )
    metadata_other = {
        "header": ["Element Name", "Tag", "N-SET"],
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "n-set"},
    }    
    second = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "2"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "1"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "3"},
        metadata_attrs=metadata_other
    )
    third = make_spec_model_with_seq(
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "R+"},
        {"elem_name": "My Element Sequence", "elem_tag": "(0101,1010)", "n-set": "R+*"},
        {"elem_name": "My Element", "elem_tag": "(0101,1011)", "n-set": "O"},
        metadata_attrs=metadata_other
    )
    return current, second, third
