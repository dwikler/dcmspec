"""JSON model store class for DICOM specification storage in dcmspec.

Provides the JSONSpecStore class for loading and saving DICOM specification models
to and from JSON files.
"""

import json
import os
from anytree import Node
from anytree.importer import JsonImporter
from anytree.exporter import JsonExporter

from dcmspec.spec_store import SpecStore
from dcmspec.spec_model import SpecModel




class JSONSpecStore(SpecStore):
    """Model store class for DICOM specification models storage in JSON format.

    Provides methods to load and save DICOM specification models to and from JSON files.
    Inherits logging from SpecStore.
    """

    def load(self, path: str) -> SpecModel:
        """Load a specification model from a JSON file.

        Args:
            path (str): The path to the JSON file to load.

        Returns:
            SpecModel: The specification model containing both metadata and content nodes.

        Raises:
            RuntimeError: If the file cannot be read, parsed, or has an invalid structure.

        """
        try:
            importer = JsonImporter()
            with open(path, "r", encoding="utf-8") as json_file:
                root = importer.read(json_file)

            # Check that the root node is named "dcmspec"
            if root.name != "dcmspec":
                raise RuntimeError(f"Invalid model structure in JSON file {path}: root node must be 'dcmspec'.")

            # Search for metadata and content nodes directly under the root
            metadata = next((node for node in root.children if node.name == "metadata"), None)
            content = next((node for node in root.children if node.name == "content"), None)

            if metadata is None or content is None:
                raise RuntimeError(
                    f"Invalid model structure in JSON file {path}: "
                    f"Both 'metadata' and 'content' nodes must be present as children of 'dcmspec'."
                )

            # Detach the model nodes from the file root node
            metadata.parent = None
            content.parent = None

            # Convert keys of column_to_attr back to integers if present in metadata
            if "column_to_attr" in metadata.__dict__:
                metadata.column_to_attr = {int(k): v for k, v in metadata.column_to_attr.items()}

            return SpecModel(metadata=metadata, content=content)
        except OSError as e:
            raise RuntimeError(f"Failed to read model data from JSON file {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON file {path}: {e}") from e

    def save(self, model: SpecModel, path: str) -> None:
        """Save a specification model to a JSON file.

        Args:
            model (SpecModel): The model object (an instance of SpecModel or a derived class)
                containing metadata and content nodes to save.
            path (str): The path to the JSON file to write.

        Returns:
            None

        Raises:
            RuntimeError: If the file cannot be written.

        """
        # Create the destination folder if it does not exist
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # Create a new root node "dcmspec"
        root_node = Node("dcmspec")

        # Temporarily add the model's metadata and content as children of the new root node
        model.metadata.parent = root_node
        model.content.parent = root_node

        try:
            exporter = JsonExporter(indent=4, sort_keys=False)
            with open(path, "w", encoding="utf-8") as json_file:
                exporter.write(root_node, json_file)
            self.logger.info(f"Attribute model saved as JSON to {path}")

        except OSError as e:
            raise RuntimeError(f"Failed to write JSON file {path}: {e}") from e

        # Detach the temporary children to leave the model unchanged
        model.metadata.parent = None
        model.content.parent = None
