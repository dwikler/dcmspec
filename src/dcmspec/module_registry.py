"""Module registry class for sharing module models across IODs in dcmspec.

Provides the ModuleRegistry class, which manages a mapping from table_id to module SpecModel.
This enables memory-efficient sharing of module models when building many IODs.

A table_id is a string identifier for a DICOM table, typically extracted from the HTML anchor tag,
for example: <a id="table_C.7-1" shape="rect"></a> yields table_id="table_C.7-1".
"""

from collections import UserDict

class ModuleRegistry(UserDict):
    """Registry for sharing module models by table_id across IODs.

    This class manages a mapping from table_id (str) to SpecModel.
    The table_id is typically a string like "table_C.7-1", as found in the HTML anchor tag:
        <a id="table_C.7-1" shape="rect"></a>
    It is used to avoid duplicating module models in memory when building many IODs.

    Access patterns:
        - registry[table_id] -> SpecModel
        - registry.get(table_id) -> SpecModel or None
        - for table_id, model in registry.items(): ...

    Example:
        ```python
        registry = ModuleRegistry()
        # When building IODs, pass registry to IODSpecBuilder(module_registry=registry)

        # Setting a module model:
        registry["table_C.7-1"] = module_model  # module_model is a SpecModel

        # Getting a module model (returns SpecModel):
        model = registry["table_C.7-1"]

        # Safe get (returns SpecModel or None):
        model = registry.get("table_C.7-1")

        # Checking if a module is present:
        if "table_C.7-1" in registry:
            ...

        # Iterating over all table_ids and models:
        for table_id, model in registry.items():
            # table_id: str, model: SpecModel
            ...
        ```

    All values in the registry are instances of SpecModel.
    
    """