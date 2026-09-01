"""Section registry class for sharing explanatory section models across modules in dcmspec.

Provides the SectionRegistry class, which manages a mapping from section_id to section SpecModel.
This enables memory-efficient sharing of section models when the same explanatory section is
referenced from multiple modules.

A section_id is a string identifier for a DICOM explanatory section, extracted from the HTML anchor
tag, for example: <a id="sect_C.7.6.16.2.2.1" shape="rect"></a> yields section_id="sect_C.7.6.16.2.2.1".
"""

from collections import UserDict

class SectionRegistry(UserDict):
    """Registry for sharing explanatory section models by section_id across modules.

    This class manages a mapping from section_id (str) to SpecModel.
    The section_id is typically a string like "sect_C.7.6.16.2.2.1", as found in the HTML anchor tag:
        <a id="sect_C.7.6.16.2.2.1" shape="rect"></a>
    It is used to avoid duplicating section models in memory when the same explanatory section is
    referenced by more than one module.

    Access patterns:
        - registry[section_id] -> SpecModel
        - registry.get(section_id) -> SpecModel or None
        - for section_id, model in registry.items(): ...

    Example:
        ```python
        registry = SectionRegistry()
        # When building modules, pass registry to ModuleSpecBuilder(section_registry=registry)

        # Setting a section model:
        registry["sect_C.7.6.16.2.2.1"] = section_model  # section_model is a SpecModel

        # Getting a section model (returns SpecModel):
        model = registry["sect_C.7.6.16.2.2.1"]

        # Safe get (returns SpecModel or None):
        model = registry.get("sect_C.7.6.16.2.2.1")

        # Checking if a section is present:
        if "sect_C.7.6.16.2.2.1" in registry:
            ...

        # Iterating over all section_ids and models:
        for section_id, model in registry.items():
            # section_id: str, model: SpecModel
            ...
        ```

    All values in the registry are instances of SpecModel.

    """
