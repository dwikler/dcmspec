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
from dcmspec.module_registry import ModuleRegistry

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
    """Orchestrates the construction of DICOM IOD specification models supporting two modes.

    - Expanded (legacy) mode: Produces a single expanded IOD model, where each IOD node has its referenced
    Module's content nodes attached as children. This is the default if no module_registry is provided.

    - Registry/reference mode: If a ModuleRegistry is provided, Module models are shared by reference via the registry,
    enabling efficient reuse and reduced memory usage when building many IODs.

    """

    def __init__(
        self,
        iod_factory: SpecFactory = None,
        module_factory: SpecFactory = None,
        logger: logging.Logger = None,
        ref_attr: str = None,
        module_registry: Optional[ModuleRegistry] = None,
    ):
        """Initialize the IODSpecBuilder.

        If no factory is provided, a default SpecFactory is used for both IOD and module models.

        Args:
            iod_factory (Optional[SpecFactory]): Factory for building the IOD model. If None, uses SpecFactory().
            module_factory (Optional[SpecFactory]): Factory for building module models. If None, uses iod_factory.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
            ref_attr (Optional[str]): Attribute name to use for Module references. If None, defaults to "ref".
            module_registry (Optional[ModuleRegistry]): Registry for sharing Module models by table_id.
                If provided, Module models are shared by reference across IODs.

        Raises:
            ValueError: If `ref_attr` is not a non-empty string.

        Note:
            The builder is initialized with factories for the IOD and module models. By default, the same
            factory is used for both, but a different factory can be provided for modules if needed.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.iod_factory = iod_factory or SpecFactory(logger=self.logger)
        self.module_factory = module_factory or self.iod_factory
        self.dom_utils = DOMUtils(logger=self.logger)
        self.ref_attr = ref_attr or "ref"
        self.module_registry = module_registry
        # Set expand flag: expand=True for legacy (expanded/copy) mode, False for registry/reference mode
        self.expand = self.module_registry is None
        if not isinstance(self.ref_attr, str) or not self.ref_attr.strip():
            raise ValueError("ref_attr must be a non-empty string.")

        
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
    ) -> tuple[SpecModel, Optional[Dict[str, SpecModel]]]:
        """Build and cache a DICOM IOD specification model from a URL.

        Warning::
            This method now returns a tuple ``(iod_model, module_models)``, which is a **breaking change** from
            previous versions that returned only the IOD model. All callers must be updated to unpack the tuple,
            or use backward-compatible wrappers if needed.

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
            tuple: (iod_model, module_models)
                - iod_model (SpecModel): The expanded IOD model (if expand=True) or the IOD model (if expand=False).
                - module_models (dict or None): The Module models dict (None if expand=True).

        Note:
            The returned `module_models` dict contains only the modules referenced by the current IOD.
            If you provided a `ModuleRegistry`, it may contain additional modules from previous or future builds.
            The registry enables sharing and reuse, but the returned dict is always specific to the current IOD.

  
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

        # Load from cache if available and not force_download
        cache_dir = self.iod_factory.config.get_param("cache_dir")
        iod_model_path = self._get_model_cache_path(json_file_name, cache_dir)
        iod_model = self._load_iod_model_from_cache(iod_model_path, force_download)
        module_models = None
        if not self.expand and iod_model is not None:
            module_models = self._load_module_models_from_cache(iod_model, cache_dir)
        if iod_model is not None and (self.expand or module_models is not None):
            self.logger.info(f"Loaded IOD model from cache: {iod_model_path}")
            return iod_model, module_models
    
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

        # --- Step 2: Build the IOD model from the DOM ---
        if progress_observer:
            progress_observer(
                Progress(-1, status=ProgressStatus.PARSING_IOD_MODULE_LIST, step=2, total_steps=total_steps)
                )
        iod_model = self._build_iod_model(dom, table_id, url, json_file_name)

        # --- Step 3: Build or load model for each module in the IOD ---
        if progress_observer:
            progress_observer(
                Progress(-1, status=ProgressStatus.PARSING_IOD_MODULES, step=3, total_steps=total_steps)
            )

        # Find all nodes with a reference attribute in the IOD Modules model
        nodes_with_ref = [node for node in iod_model.content.children if hasattr(node, self.ref_attr)]

        # Build or load module models for each referenced section
        module_models = self._build_module_models(
            nodes_with_ref, dom, url, step=3, total_steps=total_steps, progress_observer=progress_observer
        )
        # Fail if no module models were found.
        if not module_models:
            raise RuntimeError("No module models were found for the referenced modules in the IOD table.")

        # --- Step 4: Create and store the iod expanded or enriched model ---
        if progress_observer:
            progress_observer(Progress(-1, status=ProgressStatus.SAVING_IOD_MODEL, step=4, total_steps=total_steps))

        # Create the expanded model from the IOD modules and module models
        if self.expand:
            expanded_iod_model = self._create_expanded_model(iod_model, module_models)

        # Cache the expanded or enriched model if a json_file_name is provided
        if json_file_name:
            iod_json_file_path = self._get_model_cache_path(
                json_file_name, self.iod_factory.config.get_param("cache_dir")
            )
            try:
                self.iod_factory.model_store.save(expanded_iod_model, iod_json_file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cache model to {iod_json_file_path}: {e}")
        else:
            self.logger.info("No json_file_name specified; IOD model not cached.")

        if self.expand:
            return expanded_iod_model, None
        else:
            return iod_model, module_models

    def _get_model_cache_path(self, json_file_name: Optional[str], cache_dir: str) -> Optional[str]:
        """Return the full path to the model cache file for the given cache_dir and json_file_name."""
        return self._get_cache_path(json_file_name, cache_dir)

    def _get_module_model_cache_path(self, module_json_file_name: str) -> Optional[str]:
        """Return the full path to the module model cache file for the current module_factory."""
        cache_dir = self.module_factory.config.get_param("cache_dir")
        return self._get_cache_path(module_json_file_name, cache_dir)

    def _get_cache_path(self, json_file_name: Optional[str], cache_dir: Optional[str]) -> Optional[str]:
        """Return the full path to a cache file in the model cache directory."""
        if json_file_name and cache_dir:
            return os.path.join(cache_dir, "model", json_file_name)
        return None

    def _load_iod_model_from_cache(self, iod_model_path: Optional[str], force_download: bool) -> Optional[SpecModel]:
        """Return the cached IOD model if available and not force_download, else None."""
        if iod_model_path and os.path.exists(iod_model_path) and not force_download:
            try:
                return self.iod_factory.model_store.load(iod_model_path)
            except Exception as e:
                self.logger.warning(
                    f"Failed to load IOD model from cache {iod_model_path}: {e}"
                )
        return None

    def _load_module_models_from_cache(self, iod_model: SpecModel, cache_dir: str) -> Optional[Dict[str, SpecModel]]:
        """Return a dict of module models loaded from cache, keyed by table_id, for the given IOD model.

        If a module is already present in the registry, it is reused and not loaded from cache again.
        """
        module_models = {}
        nodes_with_ref = [node for node in iod_model.content.children if hasattr(node, self.ref_attr)]
        for node in nodes_with_ref:
            table_id = getattr(node, "table_id", None)
            if table_id:
                # Use registry if available and module already present
                if self.module_registry is not None and table_id in self.module_registry:
                    module_model = self.module_registry[table_id]
                else:
                    module_json_file_name = f"{table_id}.json"
                    module_json_file_path = self._get_module_model_cache_path(module_json_file_name)
                    if module_json_file_path and os.path.exists(module_json_file_path):
                        try:
                            module_model = self.module_factory.model_store.load(module_json_file_path)
                            # Optionally, also populate the registry
                            if self.module_registry is not None:
                                self.module_registry[table_id] = module_model
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load module model from cache {module_json_file_path}: {e}"
                            )
                            continue
                    else:
                        continue  # If not in registry and not in cache, skip (or could trigger build if desired)
                module_models[table_id] = module_model
        return module_models or None

    def _build_iod_model(self, dom, table_id, url, json_file_name):
        """Build the IOD Module List model, without caching."""
        # Build IOD model without caching as iod enriched or expanded model will be cached separately
        return self.iod_factory.build_model(
            doc_object=dom,
            table_id=table_id,
            url=url,
            json_file_name=None,
        )

    def _build_module_models(
        self,
        nodes_with_ref: List[Any],
        dom: Any,
        url: str,
        step: int,
        total_steps: int,
        progress_observer: Optional['ProgressObserver'] = None
    ) -> Dict[str, Any]:
        """Build or load module models for each referenced section, reporting progress.

        If a module is already present in the registry, it is reused and not loaded from cache again.
        """
        module_models: Dict[str, Any] = {}

        # Initialize progress tracking
        total_modules = len(nodes_with_ref)
        if progress_observer and total_modules > 0:
            progress_observer(
                Progress(0, status=ProgressStatus.PARSING_IOD_MODULES, step=step, total_steps=total_steps)
            )
        # Iterate over nodes with references to modules
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

            # Enrich iod module node with the module's table_id for reference to registry.
            setattr(node, "table_id", module_table_id)

            # Load the module model from cache or registry, or build it if not found
            module_model = self._get_or_build_module_model(
                module_table_id, dom, url, progress_observer
            )
            # Add Module model to dict
            if module_model is not None:
                module_models[module_table_id] = module_model

            # Update progress
            if progress_observer and total_modules > 0:
                percent = calculate_percent(idx + 1, total_modules)
                progress_observer(Progress(
                    percent,
                    status=ProgressStatus.PARSING_IOD_MODULES,
                    step=step,
                    total_steps=total_steps
                ))
        return module_models

    def _get_or_build_module_model(
        self,
        module_table_id: str,
        dom: Any,
        url: str,
        progress_observer: Optional['ProgressObserver'] = None
    ) -> Optional[Any]:
        """Get or build a module model for the given table_id, using registry and cache as appropriate."""
        # Use registry if available and module already present
        if self.module_registry is not None and module_table_id in self.module_registry:
            return self.module_registry[module_table_id]
        
        # Attempt to load from cache
        module_json_file_name = f"{module_table_id}.json"
        module_json_file_path = self._get_module_model_cache_path(module_json_file_name)
        if module_json_file_path and os.path.exists(module_json_file_path):
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
            # Build the module model without caching (it will be cached when building the IOD model)
            module_model = self.module_factory.build_model(
                doc_object=dom,
                table_id=module_table_id,
                url=url,
                json_file_name=module_json_file_name,
                progress_observer=progress_observer,
            )
        # Store in registry if using reference mode
        if self.module_registry is not None:
            self.module_registry[module_table_id] = module_model
        return module_model

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
            table_id = getattr(iod_node, "table_id", None)
            if table_id and table_id in module_models:
                module_content = module_models[table_id].content
                for child in list(module_content.children):
                    child.parent = iod_node
            iod_node.parent = iod_content

        # Create and return the expanded model
        return SpecModel(metadata=iod_metadata, content=iod_content)