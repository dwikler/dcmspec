"""Module registry class for sharing module models across IODs in dcmspec.

Provides the ModuleRegistry class, which manages a mapping from table_id to module SpecModel.
This enables memory-efficient sharing of module models when building many IODs.

A table_id is a string identifier for a DICOM table, typically extracted from the HTML anchor tag,
for example: <a id="table_C.7-1" shape="rect"></a> yields table_id="table_C.7-1".
"""

from typing import Dict
from dcmspec.spec_model import SpecModel

class ModuleRegistry:
    """Registry for sharing module models by table_id across IODs.

    This class manages a mapping from table_id (str) to SpecModel.
    The table_id is typically a string like "table_C.7-1", as found in the HTML anchor tag:
        <a id="table_C.7-1" shape="rect"></a>
    It is used to avoid duplicating module models in memory when building many IODs.

    Example usage:
        registry = ModuleRegistry()
        # When building IODs, pass registry to IODSpecBuilder(module_registry=registry)

        # Setting a module model:
        registry["table_C.7-1"] = module_model

        # Getting a module model:
        model = registry["table_C.7-1"]

        # Checking if a module is present:
        if "table_C.7-1" in registry:
            ...

        # Iterating over all table_ids and models:
        for table_id, model in registry.items():
            ...
    """

    def __init__(self):
        """Initialize an empty module registry."""
        self._modules: Dict[str, SpecModel] = {}

    def __contains__(self, table_id: str) -> bool:
        """Return True if the registry contains a module for the given table_id.

        Args:
            table_id (str): The table ID to check (e.g., "table_C.7-1").

        Returns:
            bool: True if present, False otherwise.

        """
        return table_id in self._modules

    def __getitem__(self, table_id: str) -> SpecModel:
        """Get the module model for the given table_id.

        Args:
            table_id (str): The table ID of the module (e.g., "table_C.7-1").

        Returns:
            SpecModel: The module model.

        Raises:
            KeyError: If the table_id is not present.

        """
        return self._modules[table_id]

    def __setitem__(self, table_id: str, model: SpecModel) -> None:
        """Set the module model for the given table_id.

        Args:
            table_id (str): The table ID of the module (e.g., "table_C.7-1").
            model (SpecModel): The module model to set.

        """
        self._modules[table_id] = model

    def items(self):
        """Return a set-like object providing a view on the registry's items.

        Returns:
            ItemsView: A view of (table_id, model) pairs.

        """
        return self._modules.items()

    def keys(self):
        """Return a set-like object providing a view on the registry's keys.

        Returns:
            KeysView: A view of table_ids.

        """
        return self._modules.keys()

    def values(self):
        """Return an object providing a view on the registry's values.

        Returns:
            ValuesView: A view of module models.

        """
        return self._modules.values()
