"""Tests for the ServiceAttributeModel class in dcmspec.service_attribute_model."""
import pytest
from anytree import Node
from dcmspec.service_attribute_model import ServiceAttributeModel

@pytest.fixture
def sample_metadata_content_and_mapping():
    """Fixture to create a sample data to create model, with a default node."""
    metadata = Node("metadata")
    metadata.header = ["Name", "DIMSE1 (SCU/SCP)", "DIMSE2 (SCU/SCP)"]
    metadata.column_to_attr = {0: "elem_name", 1: "dimse1", 2: "dimse2"}
    content = Node("content")
    dimse_mapping = {
        "ALL_DIMSE": {1: "dimse1", 2: "dimse2"},
        "DIMSE1": {1: "dimse1"},
        "DIMSE2": {2: "dimse2"},
    }
    node = Node("row", parent=content)
    setattr(node, "elem_name", "attr1")
    setattr(node, "dimse1", "1/1")
    setattr(node, "dimse2", "3/1")
    return metadata, content, dimse_mapping, node

def test_select_dimse(sample_metadata_content_and_mapping):
    """Test that select_dimse filters attributes and headers as expected."""
    metadata, content, dimse_mapping, node = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE1")
    assert hasattr(node, "elem_name")
    assert hasattr(node, "dimse1")
    assert not hasattr(node, "dimse2")
    assert metadata.header == ["Name", "DIMSE1 (SCU/SCP)"]
    assert set(metadata.column_to_attr.values()) == {"elem_name", "dimse1"}

def test_select_dimse_warns_if_dimse_not_found(sample_metadata_content_and_mapping, caplog):
    """Test that select_dimse logs a warning and does nothing if dimse is not in DIMSE_MAPPING."""
    metadata, content, dimse_mapping, node = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    with caplog.at_level("WARNING"):
        model.select_dimse("NOT_A_DIMSE")
    assert "DIMSE 'NOT_A_DIMSE' not found in DIMSE_MAPPING" in caplog.text
    # The model should remain unchanged
    assert hasattr(node, "dimse1")
    assert hasattr(node, "dimse2")
    assert metadata.header == ["Name", "DIMSE1 (SCU/SCP)", "DIMSE2 (SCU/SCP)"]
    assert set(metadata.column_to_attr.values()) == {"elem_name", "dimse1", "dimse2"}

def test_select_role_with_comment(sample_metadata_content_and_mapping):
    """Test that select_role adds comment column/header if a comment is present."""
    metadata, content, dimse_mapping, node = sample_metadata_content_and_mapping
    setattr(node, "dimse2", "3\nThis is a comment")
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

def test_select_role_without_comment(sample_metadata_content_and_mapping):
    """Test that select_role does not add comment column/header if no comment is present."""
    metadata, content, dimse_mapping, node = sample_metadata_content_and_mapping
    setattr(node, "dimse2", "3")
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    model.select_dimse("DIMSE2")
    model.select_role("SCU")
    assert getattr(node, "dimse2") == "3"
    assert not hasattr(node, "comment")
    assert any("SCU" in h for h in metadata.header)
    assert all("SCU/SCP" not in h for h in metadata.header)
    assert "comment" not in metadata.column_to_attr.values()
    assert "Comment" not in metadata.header

def test_select_role_raises_if_select_dimse_not_called(sample_metadata_content_and_mapping):
    """Test that select_role raises RuntimeError if select_dimse was not called first."""
    metadata, content, dimse_mapping, _ = sample_metadata_content_and_mapping
    model = ServiceAttributeModel(metadata, content, dimse_mapping)
    with pytest.raises(RuntimeError, match="select_dimse must be called before select_role."):
        model.select_role("SCU")