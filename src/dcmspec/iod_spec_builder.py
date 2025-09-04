"""Builder for expanded DICOM IOD specification models in dcmspec.

This module provides the IODSpecBuilder class, which coordinates the construction of a 
DICOM IOD model, combining the IOD Modules and Module Attributes models.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from anytree import Node
from bs4 import BeautifulSoup

from dcmspec.dom_utils import DOMUtils
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_model import SpecModel

# BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
from typing import Callable
from dcmspec.progress import (
    Progress,
    ProgressStatus,
    ProgressObserver,
    add_progress_step,
    calculate_percent,
    handle_legacy_callback,
)
# END LEGACY SUPPORT

class IODSpecBuilder:
    """Orchestrates the construction of a expanded DICOM IOD specification model.

    The IODSpecBuilder uses a factory to build the IOD Modules model and, for each referenced module,
    uses a (possibly different) factory to build and cache the Module models. It then assembles a new
    model with the IOD nodes and their referenced module nodes as children, and caches the expanded model.
    """

    def __init__(
        self,
        iod_factory: SpecFactory = None,
        module_factory: SpecFactory = None,
        logger: logging.Logger = None,
        ref_attr: str = None,
    ):
        """Initialize the IODSpecBuilder.

        If no factory is provided, a default SpecFactory is used for both IOD and module models.

        Args:
            iod_factory (Optional[SpecFactory]): Factory for building the IOD model. If None, uses SpecFactory().
            module_factory (Optional[SpecFactory]): Factory for building module models. If None, uses iod_factory.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
            ref_attr (Optional[str]): Attribute name to use for module references. If None, defaults to "ref".

        The builder is initialized with factories for the IOD and module models. By default, the same
        factory is used for both, but a different factory can be provided for modules if needed.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.iod_factory = iod_factory or SpecFactory(logger=self.logger)
        self.module_factory = module_factory or self.iod_factory
        self.dom_utils = DOMUtils(logger=self.logger)
        self.ref_attr = ref_attr or "ref"

    def build_from_url(
        self,
        url: str,
        cache_file_name: str,
        table_id: str,
        force_download: bool = False,
        progress_observer: 'Optional[ProgressObserver]' = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: 'Optional[Callable[[int], None]]' = None,
        # END LEGACY SUPPORT
        json_file_name: str = None,
        **kwargs: object,
    ) -> SpecModel:
        """Build and cache a DICOM IOD specification model from a URL.

        This method orchestrates the full workflow:
        - Loads or downloads the IOD table and builds/caches the IOD model using the iod_factory.
        - Finds all nodes in the IOD model with a "ref" attribute, indicating a referenced module.
        - For each referenced module, loads or parses and caches the module model using the module_factory.
        - Assembles a new expanded model, where each IOD node has its referenced module's content node as a child.
        - Uses the first module's metadata header and version for the expanded model's metadata.
        - Caches the expanded model if a json_file_name is provided.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            table_id (str): The ID of the IOD table to parse.
            force_download (bool): If True, always download the input file and generate the model even if cached.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
                See the Note below for details on the progress events and their properties.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.            
            json_file_name (str, optional): Filename to save the cached expanded JSON model.
            **kwargs: Additional arguments for model construction.

        Returns:
            SpecModel: The expanded model with IOD and module content.
    
        Note:
            If a progress observer accepting a Progress object is provided, progress events are as follows:
            
            - **Step 1 (DOWNLOADING_IOD):** Events include `status=DOWNLOADING_IOD`, `step=1`,
            `total_steps=4`, and a meaningful `percent` value.
            - **Step 2 (PARSING_IOD_MODULE_LIST):** Events include `status=PARSING_IOD_MODULE_LIST`, `step=2`,
            `total_steps=4`, and `percent == -1` (indeterminate).
            - **Step 3 (PARSING_IOD_MODULES):** Events include `status=PARSING_IOD_MODULES`, `step=3`,
                `total_steps=4`, and a meaningful `percent` value.
            - **Step 4 (SAVING_IOD_MODEL):** Events include `status=SAVING_IOD_MODEL`, `step=4`,
                `total_steps=4`, and `percent == -1` (indeterminate).

            For example usage in a client application,
            see [`ProgressStatus`](progress.md#dcmspec.progress.ProgressStatus).

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        # Load from cache if the expanded IOD model is already present
        cached_model = self._load_expanded_model_from_cache(json_file_name, force_download)
        if cached_model is not None:
            cached_model.logger = self.logger
            return cached_model

        total_steps = 4  # 1=download, 2=parse IOD, 3=build modules, 4=save

        # --- Step 1: Load the DOM from cache file or download and cache DOM in memory ---
        if progress_observer:
            @add_progress_step(step=1, total_steps=total_steps, status=ProgressStatus.DOWNLOADING_IOD)
            def step1_progress_observer(progress):
                progress_observer(progress)
        else:
            step1_progress_observer = None
        dom = self.iod_factory.load_document(
            url=url,
            cache_file_name=cache_file_name,
            force_download=force_download,
            progress_observer=step1_progress_observer,
            # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
            progress_callback=progress_observer,
            # END LEGACY SUPPORT
        )

        # --- Step 2: Build the IOD Module List model from the DOM ---
        if progress_observer:
            progress_observer(
                Progress(-1, status=ProgressStatus.PARSING_IOD_MODULE_LIST, step=2, total_steps=total_steps)
                )
        iodmodules_model = self.iod_factory.build_model(
            doc_object=dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
        )

        # --- Step 3: Build or load model for each module in the IOD ---
        if progress_observer:
            progress_observer(
                Progress(-1, status=ProgressStatus.PARSING_IOD_MODULES, step=3, total_steps=total_steps)
            )

        # Find all nodes with a reference attribute in the IOD Modules model
        nodes_with_ref = [node for node in iodmodules_model.content.children if hasattr(node, self.ref_attr)]

        # Build or load module models for each referenced section
        module_models = self._build_module_models(
            nodes_with_ref, dom, url, step=3, total_steps=total_steps, progress_observer=progress_observer
        )
        # Fail if no module models were found.
        if not module_models:
            raise RuntimeError("No module models were found for the referenced modules in the IOD table.")

        # --- Step 4: Create and store the expanded model with IOD and module content ---
        if progress_observer:
            progress_observer(Progress(-1, status=ProgressStatus.SAVING_IOD_MODEL, step=4, total_steps=total_steps))

        # Create the expanded model from the IOD modules and module models
        iod_model = self._create_expanded_model(iodmodules_model, module_models)

        # Cache the expanded model if a json_file_name was provided
        if json_file_name:
            iod_json_file_path = os.path.join(
                self.iod_factory.config.get_param("cache_dir"), "model", json_file_name
            )
            try:
                self.iod_factory.model_store.save(iod_model, iod_json_file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cache expanded model to {iod_json_file_path}: {e}")
        else:
            self.logger.info("No json_file_name specified; IOD model not cached.")

        return iod_model

    def _load_expanded_model_from_cache(self, json_file_name: str, force_download: bool) -> SpecModel | None:
        """Return the cached expanded IOD model if available and not force_download, else None."""
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
                    f"Failed to load expanded IOD model from cache {iod_json_file_path}: {e}"
                )
        return None

    def _build_module_models(
        self,
        nodes_with_ref: List[Any],
        dom: Any,
        url: str,
        step: int,
        total_steps: int,
        progress_observer: Optional['ProgressObserver'] = None
    ) -> Dict[str, Any]:
        """Build or load module models for each referenced section, reporting progress."""
        module_models: Dict[str, Any] = {}
        total_modules = len(nodes_with_ref)
        if progress_observer and total_modules > 0:
            progress_observer(
                Progress(0, status=ProgressStatus.PARSING_IOD_MODULES, step=step, total_steps=total_steps)
                )
        for idx, node in enumerate(nodes_with_ref):
            ref_value = getattr(node, self.ref_attr, None)
            section_id = self._get_section_id_from_ref(ref_value)
            if not section_id:
                continue

            module_table_id = self.dom_utils.get_table_id_from_section(dom, section_id)
            self.logger.debug(f"First Module table_id for section_id={repr(section_id)}: {repr(module_table_id)}")
            if not module_table_id:
                self.logger.warning(f"No table found for section id {section_id}")
                continue

            module_json_file_name = f"{module_table_id}.json"
            module_json_file_path = os.path.join(
                self.module_factory.config.get_param("cache_dir"), "model", module_json_file_name
            )
            if os.path.exists(module_json_file_path):
                try:
                    module_model = self.module_factory.model_store.load(module_json_file_path)
                except Exception as e:
                    self.logger.warning(f"Failed to load module model from cache {module_json_file_path}: {e}")
                    module_model = self.module_factory.build_model(
                        doc_object=dom,
                        table_id=module_table_id,
                        url=url,
                        json_file_name=module_json_file_name,
                        progress_observer=progress_observer,
                    )
            else:
                module_model = self.module_factory.build_model(
                    doc_object=dom,
                    table_id=module_table_id,
                    url=url,
                    json_file_name=module_json_file_name,
                    progress_observer=progress_observer,
                )
            module_models[section_id] = module_model
            if progress_observer and total_modules > 0:
                percent = calculate_percent(idx + 1, total_modules)
                progress_observer(Progress(
                    percent,
                    status=ProgressStatus.PARSING_IOD_MODULES,
                    step=step,
                    total_steps=total_steps
                ))
        return module_models

    def _get_section_id_from_ref(self, ref_value: str) -> Optional[str]:
        """Normalize a ref_value (plain text or HTML anchor) to a section_id.

        For HTML, extract the href after '#'. For plain text, always prepend 'sect_'.
        Strips whitespace for robust lookup.
        (Do NOT lowercase: DICOM IDs are mixed case and BeautifulSoup search is case-sensitive.)
        """
        if not ref_value:
            return None
        if "<a " not in ref_value:
            # Always prepend 'sect_' for plain text references, strip only
            section_id = f"sect_{ref_value.strip()}"
            self.logger.debug(f"Extracted section_id from plain text reference: {repr(section_id)}")
            return section_id
        soup = BeautifulSoup(ref_value, "lxml-xml")
        # Find the anchor with class "xref" (the actual module reference)
        anchor = soup.find("a", class_="xref")
        if anchor and anchor.has_attr("href"):
            href = anchor["href"].strip()
            section_id = href.split("#", 1)[-1] if "#" in href else href
            section_id = section_id.strip()
            self.logger.debug(f"Extracted section_id from HTML reference: {repr(section_id)}")
            return section_id
        else:
            self.logger.debug(f"No section_id could be extracted from ref_value={repr(ref_value)}")
            return None

    def _create_expanded_model(self, iodmodules_model: SpecModel, module_models: dict) -> SpecModel:
        """Create the expanded model by attaching Module nodes content to IOD nodes."""
        # Use the first module's metadata node for the expanded model
        first_module = next(iter(module_models.values()))
        iod_metadata = first_module.metadata
        iod_metadata.table_id = iodmodules_model.metadata.table_id

        # The content node will have as children the IOD model's nodes,
        # and for each referenced module, its content's children will be attached directly under the iod node
        iod_content = Node("content")
        for iod_node in iodmodules_model.content.children:
            ref_value = getattr(iod_node, self.ref_attr, None)
            section_id = self._get_section_id_from_ref(ref_value)
            if section_id and section_id in module_models:
                module_content = module_models[section_id].content
                for child in list(module_content.children):
                    child.parent = iod_node
            iod_node.parent = iod_content

        # Create and return the expanded model
        return SpecModel(metadata=iod_metadata, content=iod_content)