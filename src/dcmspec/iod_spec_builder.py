"""Builder for combined DICOM IOD+modules specification models in dcmspec.

This module provides the IODSpecBuilder class, which coordinates the construction of a 
DICOM IOD model, combining the iod modeules and module attributes model.
"""
import logging
import os

from anytree import Node
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_model import SpecModel

class IODSpecBuilder:
    """Orchestrates the construction of a combined DICOM IOD+modules specification model.

    The IODSpecBuilder uses a factory to build the main IOD model and, for each referenced module,
    uses a (possibly different) factory to build and cache the module models. It then assembles a new
    model with the IOD nodes and their referenced module nodes as children, and caches the combined model.
    """

    def __init__(self, iod_factory=None, module_factory=None, logger: logging.Logger = None):
        """Initialize the IODSpecBuilder.

        If no factory is provided, a default SpecFactory is used for both IOD and module models.

        Args:
            iod_factory (Optional[SpecFactory]): Factory for building the IOD model. If None, uses SpecFactory().
            module_factory (Optional[SpecFactory]): Factory for building module models. If None, uses iod_factory.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        The builder is initialized with factories for the IOD and module models. By default, the same
        factory is used for both, but a different factory can be provided for modules if needed.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.iod_factory = iod_factory or SpecFactory(logger=self.logger)
        self.module_factory = module_factory or self.iod_factory

    def build_from_url(
        self,
        url: str,
        cache_file_name: str,
        table_id: str,
        force_download: bool = False,
        json_file_name: str = None,
        **kwargs,
    ):
        """Build and cache a DICOM IOD specification model from a URL.

        This method orchestrates the full workflow:
        - Loads or downloads the IOD table and builds/caches the IOD model using the iod_factory.
        - Finds all nodes in the IOD model with a "ref" attribute, indicating a referenced module.
        - For each referenced module, loads or parses and caches the module model using the module_factory.
        - Assembles a new combined model, where each IOD node has its referenced module's content node as a child.
        - Uses the first module's metadata header and version for the combined model's metadata.
        - Caches the combined model if a json_file_name is provided.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            table_id (str): The ID of the IOD table to parse.
            force_download (bool): If True, always download the input file and generate the model even if cached.
            json_file_name (str, optional): Filename to save the cached combined JSON model.
            **kwargs: Additional arguments for model construction.

        Returns:
            SpecModel: The combined model with IOD and module content.

        """
        # Check if the combined model is already cached and valid
        iod_json_file_path = None
        if json_file_name:
            iod_json_file_path = os.path.join(
                self.iod_factory.config.get_param("cache_dir"), "model", json_file_name
            )
        if iod_json_file_path and os.path.exists(iod_json_file_path) and not force_download:
            try:
                return self.iod_factory.model_store.load(iod_json_file_path)
            except Exception as e:
                self.logger.warning(
                    f"Failed to load combined model from cache {iod_json_file_path}: {e}"
                )
        # Only load/cache the DOM and build the model if not cached
        dom = self.iod_factory.load_dom(
            url=url,
            cache_file_name=cache_file_name,
            force_download=force_download,
        )

        # Build/load the IOD model from the DOM
        iodmodules_model = self.iod_factory.build_model(
            dom=dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            **kwargs,
        )

        # Find all nodes with a "ref" attribute in the main model
        nodes_with_ref = [node for node in iodmodules_model.content.children if hasattr(node, "ref")]

        # Collect module models for each referenced section
        module_models = {}
        for node in nodes_with_ref:
            ref_value = getattr(node, "ref", None)
            if not ref_value:
                continue
            section_id = f"sect_{ref_value}"
            table_id = self.iod_factory.table_parser.get_table_id_from_section(dom, section_id)
            if not table_id:
                self.logger.warning(f"No table found for section id {section_id}")
                continue

            module_json_file_name = f"{table_id}.json"

            module_model = self.module_factory.build_model(
                dom=dom,
                table_id=table_id,
                url=url,
                json_file_name=module_json_file_name,
            )

            module_models[ref_value] = module_model

        # Fail if no module models were found.
        if not module_models:
            raise RuntimeError("No module models were found for the referenced modules in the IOD table.")

        # Use the first module's metadata node for the combined model
        first_module = next(iter(module_models.values()))
        iod_metadata = first_module.metadata

        # The content node will have as children the IOD model's nodes,
        # and for each referenced module, its content's children will be attached directly under the iod node
        iod_content = Node("content")
        for iod_node in iodmodules_model.content.children:
            ref_value = getattr(iod_node, "ref", None)
            if ref_value and ref_value in module_models:
                module_content = module_models[ref_value].content
                # Attach each child of the module content directly under the iod node
                for child in list(module_content.children):
                    child.parent = iod_node
            iod_node.parent = iod_content

        # Create the combined model
        iod_model = SpecModel(metadata=iod_metadata, content=iod_content)

        # Cache the combined model if a json_file_name was provided
        if json_file_name:
            iod_json_file_path = os.path.join(
                self.iod_factory.config.get_param("cache_dir"), "model", json_file_name
            )
            try:
                self.iod_factory.model_store.save(iod_model, iod_json_file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cache combined model to {iod_json_file_path}: {e}")

        return iod_model
