import json
import os
from typing import Any, Tuple
from dcmspec.spec_store import SpecStore
from anytree import Node
from anytree.importer import JsonImporter
from anytree.exporter import JsonExporter


class JSONSpecStore(SpecStore):
    def load(self, path: str) -> Tuple[Node, Node]:
        """Returns metadata and content from the JSON file"""
        try:
            importer = JsonImporter()
            with open(path, "r", encoding="utf-8") as json_file:
                root = importer.read(json_file)

            # Search for metadata and content nodes
            metadata = next((node for node in root.children if node.name == "metadata"), None)
            content = next((node for node in root.children if node.name == "content"), None)
            # Detach the model nodes from the file root node
            metadata.parent = None
            content.parent = None

            # Convert keys of column_to_attr back to integers if present in metadata
            if "column_to_attr" in metadata.__dict__:
                metadata.column_to_attr = {int(k): v for k, v in metadata.column_to_attr.items()}

            return metadata, content
        except OSError as e:
            raise RuntimeError(f"Failed to read model data from JSON file {path}: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON file {path}: {e}")

    def save(self, model: Any, path: str) -> None:
        """
        Saves a model to a JSON file.
        Raises a RuntimeError if the file cannot be written.
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
            raise RuntimeError(f"Failed to write JSON file {path}: {e}")

        # Detach the temporary children to leave the model unchanged
        model.metadata.parent = None
        model.content.parent = None
