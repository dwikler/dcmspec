"""Default name_attr, column_to_attr and DIMSE mappings for DICOM Services attribute specification tables.

- UPS:  For PS3.4 CC.2.5.1 Unified Procedure Step.
- MPPS: For PS3.4 F.7.2.1 Modality Performed Procedure Step.

Each mapping provides a default `column_to_attr` dictionary, a corresponding DIMSE mapping
dictionary and `name_attr` string for use with ServiceAttributeModel and related classes.

Note:
    These mappings are designed to be used together. If you use custom attribute names,
    you must adapt both mappings accordingly.

Note:
    These constants are intended as read-only defaults. If you need to modify a mapping,
    make a copy first (e.g., `UPS_COLUMNS_MAPPING.copy()` or `copy.deepcopy(UPS_DIMSE_MAPPING)`).
    Modifying the shared constants directly can lead to unexpected behavior elsewhere in your code.
    Only the dictionary constants (e.g., `*_COLUMNS_MAPPING`, `*_DIMSE_MAPPING`) need to be copied.
    String constants (e.g., `*_NAME_ATTR`) are immutable and do not need to be copied.

    
Example usage:
    ```python
    from dcmspec.service_attribute_defaults import UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR
    factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(),
        column_to_attr=UPS_COLUMNS_MAPPING.copy(),
        name_attr=UPS_NAME_ATTR,
        config=config
    )
    model = factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        table_id=table_id,
        force_download=False,
        model_kwargs={"dimse_mapping": copy.deepcopy(UPS_DIMSE_MAPPING)},
        )
    ```

"""

UPS_COLUMNS_MAPPING = {
    0: "elem_name",
    1: "elem_tag",
    2: "dimse_ncreate",
    3: "dimse_nset",
    4: "dimse_final",
    5: "dimse_nget",
    6: "key_matching",
    7: "key_return",
    8: "type_remark",
}
"""dict: Default column-to-attribute mapping for UPS attribute tables."""

UPS_NAME_ATTR = "elem_name"
"""str: Default name_attr for UPS attribute tables."""

UPS_DIMSE_MAPPING = {
    "ALL_DIMSE": {
        "attributes": [
            "dimse_ncreate", "dimse_nset", "dimse_final", "dimse_nget",
            "key_matching", "key_return", "type_remark"
        ]
    },
    "N-CREATE": {
        "attributes": ["dimse_ncreate", "type_remark"],
        "req_attributes": ["dimse_ncreate"],
        "req_separator": "/"
    },
    "N-SET": {
        "attributes": ["dimse_nset", "type_remark"],
        "req_attributes": ["dimse_nset"],
        "req_separator": "/"
    },
    "N-GET": {
        "attributes": ["dimse_nget", "type_remark"],
        "req_attributes": ["dimse_nget"],
        "req_separator": "/"
    },
    "C-FIND": {
        "attributes": ["key_matching", "key_return", "type_remark"],
        "req_attributes": ["key_matching", "key_return"]
    },
    "FINAL": {
        "attributes": ["dimse_final", "type_remark"],
        "req_attributes": ["dimse_final"]
    },
}
"""dict: Default DIMSE mapping for UPS attribute tables."""

MPPS_COLUMNS_MAPPING = {
    0: "elem_name",
    1: "elem_tag",
    2: "dimse_ncreate",
    3: "dimse_nset",
    4: "dimse_final",
}
"""dict: Default column-to-attribute mapping for MPPS attribute tables."""

MPPS_NAME_ATTR = "elem_name"
"""str: Default name_attr for MPPS attribute tables."""

MPPS_DIMSE_MAPPING = {
    "ALL_DIMSE": {
        "attributes": [
            "dimse_ncreate", "dimse_nset", "dimse_final"
        ]
    },
    "N-CREATE": {
        "attributes": ["dimse_ncreate"],
        "req_attributes": ["dimse_ncreate"],
        "req_separator": "/"
    },
    "N-SET": {
        "attributes": ["dimse_nset"],
        "req_attributes": ["dimse_nset"],
        "req_separator": "/"
    },
    "FINAL": {
        "attributes": ["dimse_final"],
        "req_attributes": ["dimse_final"]
    },
}
"""dict: Default DIMSE mapping for MPPS attribute tables."""
