"""ServiceAttributeModel class for DICOM DIMSE/role-based attribute filtering in dcmspec.

Provides the ServiceAttributeModel class for filtering DICOM Services specification models
where several DIMSE Services and Roles requirements are mixed in one table. This class
enables selection and filtering of attributes and columns based on DIMSE service and role,
allowing extraction of service- and role-specific attribute sets from a combined table.
"""

from anytree import PreOrderIter

from dcmspec.spec_model import SpecModel

class ServiceAttributeModel(SpecModel):
    """A model for DICOM Services with mixed DIMSE and role requirements.

    ServiceAttributeModel extends SpecModel to support selection and filtering of attributes
    and columns based on DIMSE service and role, using a provided mapping. It enables
    extraction of service- and role-specific attribute sets from tables where multiple
    DIMSE Services and Roles are combined.
    """

    def __init__(self, metadata, content, dimse_mapping, logger=None):
        """Initialize the ServiceAttributeModel.

        Sets up the model with metadata, content, and a DIMSE mapping for filtering.
        Initializes the DIMSE and role selection to None.

        Args:
            metadata: Node holding table and document metadata.
            content: Node holding the hierarchical content tree of the DICOM specification.
            dimse_mapping: Mapping defining DIMSE and role-based attribute requirements.
            logger (optional): Logger instance to use. If None, a default logger is created.

        Example:
            ```python
            UPS_DIMSE_MAPPING = {
                "ALL_DIMSE": {
                    2: "dimse_ncreate",
                    3: "dimse_nset",
                    4: "dimse_final",
                    5: "dimse_nget",
                    6: "key_matching",
                    7: "key_return",
                    8: "type_remark"
                },
                "N-CREATE": {2: "dimse_ncreate", 8: "type_remark"},
                "N-SET": {3: "dimse_nset", 8: "type_remark"},
                "N-GET": {5: "dimse_nget", 8: "type_remark"},
                "C-FIND": {6: "key_matching", 7: "key_return", 8: "type_remark"},
                "FINAL": {4: "dimse_final", 8: "type_remark"},
            }
            model = ServiceAttributeModel(metadata, content, UPS_DIMSE_MAPPING)
            ```
            
        """
        super().__init__(metadata, content, logger=logger)
        self.DIMSE_MAPPING = dimse_mapping
        self.dimse = None
        self.role = None


    def select_dimse(self, dimse):
        """Select the attribute model for the specified DIMSE SOP Class.

        Args:
            dimse: The key of DIMSE_MAPPING to select.

        """
        if dimse not in self.DIMSE_MAPPING:
            self.logger.warning(f"DIMSE '{dimse}' not found in DIMSE_MAPPING")
            return
        else:
            self.dimse = dimse
        dimse_attributes = set(self.DIMSE_MAPPING[dimse].values())
        all_attributes = set(self.DIMSE_MAPPING["ALL_DIMSE"].values())

        # Remove node attributes that are not belonging to the DIMSE
        for node in PreOrderIter(self.content):
            for attr in list(node.__dict__.keys()):
                if attr in all_attributes and attr not in dimse_attributes:
                    delattr(node, attr)

        # Determine the columns indices corresponding to the selected DIMSE
        dimse_indices = {key for key, value in self.DIMSE_MAPPING[dimse].items()}

        # Remove header items that are not belonging to the DIMSE
        if hasattr(self.metadata, "header"):
            self.metadata.header = [
                cell for i, cell in enumerate(self.metadata.header)
                if i in dimse_indices or i not in self.DIMSE_MAPPING["ALL_DIMSE"]
            ]

        # Update the column_to_attr to only include attributes belonging to the selected DIMSE
        if hasattr(self.metadata, "column_to_attr"):
            self.metadata.column_to_attr = {
                key: value
                for key, value in self.metadata.column_to_attr.items()
                if value in dimse_attributes or key not in self.DIMSE_MAPPING["ALL_DIMSE"]
            }

    def select_role(self, role):
        """Select the attribute model for the specified Role of the selected DIMSE Service User.

        Note:
            You must call select_dimse() before calling select_role(), or a RuntimeError will be raised.

        Raises:
            RuntimeError: If select_dimse was not called before select_role.
            
        """
        if role is None:
            return
        if self.dimse is None or self.dimse == "ALL_DIMSE":
            raise RuntimeError("select_dimse must be called before select_role.")
        self.role = role
        if self.dimse in ("C-FIND", "FINAL", None):
            self.logger.info(f"No role-specific requirements for {self.dimse}")
            return

        attribute_name = self._get_dimse_attribute_name()

        comment_needed = False

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
                sub_parts = optionality.split("/", 1)
                if len(sub_parts) > 1:
                    setattr(node, attribute_name, sub_parts[0] if role == "SCU" else sub_parts[1])

        # Add the comment column and header only if needed
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

    def _get_dimse_attribute_name(self):
        dimse_attr_key = next(iter(self.DIMSE_MAPPING[self.dimse]))
        return self.DIMSE_MAPPING[self.dimse][dimse_attr_key]
