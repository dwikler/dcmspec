"""Tests for the ServiceAttributeModel class in dcmspec.service_attribute_model."""
import pytest
from anytree import Node
from dcmspec.service_attribute_model import ServiceAttributeModel

@pytest.fixture
def sample_metadata_content_and_mapping():
    """Fixture to create a sample ServiceAttributeModel and node, with helpers to reset node values.
    
    Includes DIMSE1 and DIMSE2 (with separator) and DIMSE3 (without separator) for comprehensive testing.
    """
    metadata = Node("metadata")
    metadata.header = ["Name", "DIMSE1 (SCU/SCP)", "DIMSE2 (SCU/SCP)", "DIMSE3"]
    metadata.column_to_attr = {0: "elem_name", 1: "dimse1", 2: "dimse2", 3: "dimse3"}
    content = Node("content")
    dimse_mapping = {
        "ALL_DIMSE": {
            "attributes": ["dimse1", "dimse2", "dimse3"]
        },
        "DIMSE1": {
            "attributes": ["dimse1"],
            "req_attributes": ["dimse1"],
            "req_separator": "/"
        },
        "DIMSE2": {
            "attributes": ["dimse2"],
            "req_attributes": ["dimse2"],
            "req_separator": "/"
        },
        "DIMSE3": {
            "attributes": ["dimse3"],
            "req_attributes": ["dimse3"]
            # No req_separator
        },
    }
    node = Node("row", parent=content)
    setattr(node, "elem_name", "attr1")
    setattr(node, "dimse1", "1/1")
    setattr(node, "dimse2", "3/1")
    setattr(node, "dimse3", "1")
    def set_node_value(attr, value):
        setattr(node, attr, value)
    return metadata, content, dimse_mapping, node, set_node_value

def test_select_dimse(sample_metadata_content_and_mapping):
    """Test that select_dimse filters attributes and headers as expected, and retains attributes not in ALL_DIMSE."""
    metadata, content, dimse_mapping, node, _ = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE1")
    # elem_name is not in ALL_DIMSE, should be retained
    assert hasattr(node, "elem_name")
    assert hasattr(node, "dimse1")
    assert not hasattr(node, "dimse2")
    assert metadata.header == ["Name", "DIMSE1 (SCU/SCP)"]
    assert set(metadata.column_to_attr.values()) == {"elem_name", "dimse1"}

def test_select_dimse_warns_if_dimse_not_found(sample_metadata_content_and_mapping, caplog):
    """Test that select_dimse logs a warning and does nothing if dimse is not in DIMSE_MAPPING."""
    metadata, content, dimse_mapping, node, _ = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    with caplog.at_level("WARNING"):
        model.select_dimse("NOT_A_DIMSE")
    assert "DIMSE 'NOT_A_DIMSE' not found in DIMSE_MAPPING" in caplog.text
    # The model should remain unchanged
    assert hasattr(node, "dimse1")
    assert hasattr(node, "dimse2")
    assert hasattr(node, "dimse3")
    assert metadata.header == ["Name", "DIMSE1 (SCU/SCP)", "DIMSE2 (SCU/SCP)", "DIMSE3"]
    assert set(metadata.column_to_attr.values()) == {"elem_name", "dimse1", "dimse2", "dimse3"}

def test_select_role_with_separator_scu(sample_metadata_content_and_mapping):
    """Test that select_role splits values using the separator and keeps the SCU part."""
    metadata, content, dimse_mapping, node, set_node_value = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE2")
    model.select_role("SCU")
    assert getattr(node, "dimse2") == "3"
    assert not hasattr(node, "comment")

def test_select_role_with_separator_scp(sample_metadata_content_and_mapping):
    """Test that select_role splits values using the separator and keeps the SCP part."""
    metadata, content, dimse_mapping, node, set_node_value = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE2")
    # Reset value to "3/1" before testing SCP
    set_node_value("dimse2", "3/1")
    model.select_role("SCP")
    assert getattr(node, "dimse2") == "1"
    assert not hasattr(node, "comment")

def test_select_role_no_separator(sample_metadata_content_and_mapping):
    """Test that select_role does nothing if no req_separator is defined for the DIMSE."""
    metadata, content, dimse_mapping, node, set_node_value = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE3")
    model.select_role("SCU")
    # Should not split or change the value
    assert getattr(node, "dimse3") == "1"
    assert not hasattr(node, "comment")
    assert "comment" not in metadata.column_to_attr.values()
    assert "Comment" not in metadata.header

def test_select_role_with_comment(sample_metadata_content_and_mapping):
    """Test that select_role adds comment column/header if a comment is present."""
    metadata, content, dimse_mapping, node, set_node_value = sample_metadata_content_and_mapping
    set_node_value("dimse2", "3\nThis is a comment")
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE2")
    model.select_role("SCU")
    assert getattr(node, "dimse2") == "3"
    assert getattr(node, "comment") == "This is a comment"
    assert any("SCU" in h for h in metadata.header)
    assert all("SCU/SCP" not in h for h in metadata.header)
    next_key = max(metadata.column_to_attr.keys())
    assert metadata.column_to_attr[next_key] == "comment"
    assert "Comment" in metadata.header

def test_select_role_raises_if_select_dimse_not_called(sample_metadata_content_and_mapping):
    """Test that select_role raises RuntimeError if select_dimse was not called first."""
    metadata, content, dimse_mapping, _, _ = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    with pytest.raises(RuntimeError, match="select_dimse must be called before select_role."):
        model.select_role("SCU")