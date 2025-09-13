"""ServiceAttributeModel class for DICOM DIMSE/role-based attribute filtering in dcmspec.

Provides the ServiceAttributeModel class for filtering DICOM Services specification models
where several DIMSE Services and Roles requirements are mixed in one table. This class
enables selection and filtering of attributes and columns based on DIMSE service and role,
allowing extraction of service- and role-specific attribute sets from a combined table.
"""

import logging
from typing import Optional, Sequence
from anytree import Node, PreOrderIter

from dcmspec.spec_model import SpecModel

class ServiceAttributeModel(SpecModel):
    """A model for DICOM Services with mixed DIMSE and role requirements.

    ServiceAttributeModel extends SpecModel to support selection and filtering of attributes
    and columns based on DIMSE service and role, using a provided mapping. It enables
    extraction of service- and role-specific attribute sets from tables where multiple
    DIMSE Services and Roles are combined.
    """

    def __init__(
        self,
        metadata: Node,
        content: Node,
        dimse_mapping: dict,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """Initialize the ServiceAttributeModel.

        Sets up the model with metadata, content, and a DIMSE mapping for filtering.
        Initializes the DIMSE and role selection to None.
            
        Args:
            metadata (Node): Node holding table and document metadata.
            content (Node): Node holding the hierarchical content tree of the DICOM specification.
            dimse_mapping (dict): Dictionary defining DIMSE and role-based attribute requirements.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        Note:
            The `dimse_mapping` argument should be a dictionary with the following structure:
            ```python
            {
                "ALL_DIMSE": {
                    "attributes": [<attribute_name>, ...]
                },
                "<DIMSE>": {
                    "attributes": [<attribute_name>, ...],
                    "req_attributes": [<attribute_name>, ...],  # optional, for role-based requirements
                    "req_separator": "<separator>",             # optional, e.g. "/"
                },
                ...
            }
            ```

        Example:
            ```python
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
            model = ServiceAttributeModel(metadata, content, UPS_DIMSE_MAPPING)
            ```

        """
        super().__init__(metadata, content, logger=logger)
        self.DIMSE_MAPPING = dimse_mapping
        self.dimse = None
        self.role = None


    def select_dimse(self, dimse: str) -> None:
        """Filter the model to only retain attributes relevant to the specified DIMSE SOP Class.

        This method updates the model so that only the attributes required for the selected
        DIMSE are kept. All other DIMSE-specific attributes are removed from the model,
        while other attributes not listed in ALL_DIMSE are retained. This enables extraction
        of a DIMSE-specific attribute set from a combined table. The model's metadata is also
        updated to reflect the retained attributes.

        Args:
            dimse (str): The key of DIMSE_MAPPING to select.

        """
        if dimse not in self.DIMSE_MAPPING:
            self.logger.warning(f"DIMSE '{dimse}' not found in DIMSE_MAPPING")
            return
        self.dimse = dimse

        dimse_info = self.DIMSE_MAPPING[dimse]
        all_dimse_info = self.DIMSE_MAPPING["ALL_DIMSE"]

        # Determine which columns/attributes to keep for this DIMSE
        dimse_attributes = dimse_info.get("attributes", [])
        all_attributes = all_dimse_info.get("attributes", [])

        self._filter_node_attributes(dimse_attributes, all_attributes)
        self._update_metadata_for_dimse(dimse_attributes, all_attributes)


    def _filter_node_attributes(self, dimse_attributes: Sequence[str], all_attributes: Sequence[str]) -> None:
        """Remove DIMSE attributes that are not belonging to the selected DIMSE."""
        for node in PreOrderIter(self.content):
            for attr in list(node.__dict__.keys()):
                # Retaining non-DIMSE attributes (not in ALL_DIMSE)
                if attr in all_attributes and attr not in dimse_attributes:
                    delattr(node, attr)

    def _update_metadata_for_dimse(self, dimse_attributes: Sequence[str], all_attributes: Sequence[str]) -> None:
        if hasattr(self.metadata, "header") and hasattr(self.metadata, "column_to_attr"):
            # Build new header and mapping, keeping original indices for column_to_attr
            new_header = []
            new_column_to_attr = {}
            for i, cell in enumerate(self.metadata.header):
                # Only keep columns that are in the selected DIMSE or not in ALL_DIMSE
                if i in self.metadata.column_to_attr:
                    attr = self.metadata.column_to_attr[i]
                    if (attr in dimse_attributes) or (attr not in all_attributes):
                        new_header.append(cell)
                        new_column_to_attr[i] = attr
            self.metadata.header = new_header
            self.metadata.column_to_attr = new_column_to_attr
        elif hasattr(self.metadata, "column_to_attr"):
            # Only update column_to_attr if no header in metadata
            self.metadata.column_to_attr = {
                key: value
                for key, value in self.metadata.column_to_attr.items()
                if (value in dimse_attributes) or (value not in all_attributes)
            }

    def select_role(self, role: str) -> None:
        """Filter the model to only retain requirements for a specific role (SCU or SCP) of the selected DIMSE.

        This method updates the model so that, for attributes with role-specific requirements (e.g., "SCU/SCP"),
        only the requirements relevant to the selected role are retained. For example, if a attribute contains
        "1/2", selecting "SCU" will keep "1" and selecting "SCP" will keep "2". Any additional comments
        after a newline are preserved in a separate "comment" attribute. The model's metadata is also
        updated to reflect the changes in attributes.

        Args:
            role (str): The role to filter for ("SCU" or "SCP").

        Note:
            You must call select_dimse() before calling select_role(), or a RuntimeError will be raised.

        Note:
            For DIMSEs that do not have explicit SCU and SCP requirements (i.e., no "req_separator" specified
            in the mapping), this function may have no effect and will not modify the model.
            
        Raises:
            RuntimeError: If select_dimse was not called before select_role.

        """
        if role is None:
            return
        if self.dimse is None or self.dimse == "ALL_DIMSE":
            raise RuntimeError("select_dimse must be called before select_role.")
        self.role = role

        dimse_info = self.DIMSE_MAPPING[self.dimse]
        req_attributes = dimse_info.get("req_attributes", [])
        req_separator = dimse_info.get("req_separator", None)

        comment_needed = self._filter_role_attributes(req_attributes, req_separator, role)
        self._update_metadata_for_role(comment_needed, role)

    def _filter_role_attributes(self, req_attributes: list, req_separator: str, role: str) -> bool:
        """Filter node attributes for the selected role, handle comments, and return if comment column is needed."""
        comment_needed = False
        for req_attr in req_attributes:
            attribute_name = req_attr
            for node in PreOrderIter(self.content):
                if hasattr(node, attribute_name):
                    value = getattr(node, attribute_name)
                    if not isinstance(value, str):
                        continue
                    # Split SCU/SCP optionality requirements and any additional comment
                    parts = value.split("\n", 1)
                    optionality = parts[0]
                    if len(parts) > 1:
                        setattr(node, attribute_name, optionality)
                        setattr(node, "comment", parts[1])
                        comment_needed = True
                    # Split SCU/SCP optionality requirements
                    if req_separator and req_separator in optionality:
                        sub_parts = optionality.split(req_separator, 1)
                        setattr(node, attribute_name, sub_parts[0] if role == "SCU" else sub_parts[1])
        return comment_needed

    def _update_metadata_for_role(self, comment_needed: bool, role: str) -> None:
        """Update metadata (header and column_to_attr) for role-specific requirements and comments."""
        if comment_needed:
            if hasattr(self.metadata, "column_to_attr") and "comment" not in self.metadata.column_to_attr.values():
                next_key = max(self.metadata.column_to_attr.keys(), default=-1) + 1
                self.metadata.column_to_attr[next_key] = "comment"
            if hasattr(self.metadata, "header") and "Comment" not in self.metadata.header:
                self.metadata.header.append("Comment")

        if hasattr(self.metadata, "header"):
            for i, header in enumerate(self.metadata.header):
                if "SCU/SCP" in header:
                    self.metadata.header[i] = header.replace("SCU/SCP", role)