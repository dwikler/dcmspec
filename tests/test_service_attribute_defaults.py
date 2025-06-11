"""Tests for the ... in dcmspec.service_attribute_default."""
from dcmspec.service_attribute_defaults import (
    UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR,
    MPPS_DIMSE_MAPPING, MPPS_COLUMNS_MAPPING, MPPS_NAME_ATTR
)
from dcmspec.service_attribute_model import ServiceAttributeModel
from anytree import Node

def test_ups_defaults_structure():
    """Test that UPS default mappings are present and have the expected structure."""
    assert isinstance(UPS_DIMSE_MAPPING, dict)
    assert isinstance(UPS_COLUMNS_MAPPING, dict)
    assert isinstance(UPS_NAME_ATTR, str)
    assert "ALL_DIMSE" in UPS_DIMSE_MAPPING
    assert "attributes" in UPS_DIMSE_MAPPING["ALL_DIMSE"]

def test_mpps_defaults_structure():
    """Test that MPPS default mappings are present and have the expected structure."""
    assert isinstance(MPPS_DIMSE_MAPPING, dict)
    assert isinstance(MPPS_COLUMNS_MAPPING, dict)
    assert isinstance(MPPS_NAME_ATTR, str)
    assert "ALL_DIMSE" in MPPS_DIMSE_MAPPING
    assert "attributes" in MPPS_DIMSE_MAPPING["ALL_DIMSE"]

def test_ups_defaults_with_model():
    """Test that ServiceAttributeModel works with UPS default mappings."""
    import copy
    metadata = Node("metadata")
    metadata.header = ["Name", "N-CREATE (SCU/SCP)", "N-SET (SCU/SCP)"]
    metadata.column_to_attr = UPS_COLUMNS_MAPPING.copy()
    content = Node("content")
    node = Node("row", parent=content)
    setattr(node, "elem_name", "attr1")
    setattr(node, "dimse_ncreate", "1/1")
    setattr(node, "dimse_nset", "2/2")
    model = ServiceAttributeModel(metadata, content, copy.deepcopy(UPS_DIMSE_MAPPING))
    model.select_dimse("N-CREATE")
    assert hasattr(node, "dimse_ncreate")
    assert not hasattr(node, "dimse_nset")

def test_mpps_defaults_with_model():
    """Test that ServiceAttributeModel works with MPPS default mappings."""
    import copy
    metadata = Node("metadata")
    metadata.header = ["Name", "N-CREATE (SCU/SCP)", "N-SET (SCU/SCP)", "FINAL (SCU/SCP)"]
    metadata.column_to_attr = MPPS_COLUMNS_MAPPING.copy()
    content = Node("content")
    node = Node("row", parent=content)
    setattr(node, "elem_name", "attr1")
    setattr(node, "dimse_ncreate", "1/1")
    setattr(node, "dimse_nset", "2/2")
    setattr(node, "dimse_final", "3/3")
    model = ServiceAttributeModel(metadata, content, copy.deepcopy(MPPS_DIMSE_MAPPING))
    model.select_dimse("N-CREATE")
    assert hasattr(node, "dimse_ncreate")
    assert not hasattr(node, "dimse_nset")
    assert not hasattr(node, "dimse_final")