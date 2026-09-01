"""Builder for DICOM module attribute models with resolved explanatory sections in dcmspec.

This module provides the ModuleSpecBuilder class, which builds a module attribute model and
resolves the DICOM Part 3 explanatory sections it references (e.g. "See Section C.7.6.16.2.2.1"
in an attribute's description), caching each section separately and sharing them across modules
via a SectionRegistry.
"""
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from anytree import Node, PreOrderIter
from bs4 import BeautifulSoup

from dcmspec.doc_handler import DocHandler
from dcmspec.progress import ProgressObserver
from dcmspec.section_registry import SectionRegistry
from dcmspec.section_spec_parser import SectionSpecParser
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_model import SpecModel


class ModuleSpecBuilder:
    """Builds a module attribute model and resolves the explanatory sections it references.

    Mirrors IODSpecBuilder's registry/reference approach for sharing models by id, but always in
    registry mode: a resolved section is never copied inline into the module's content tree (a
    section's prose doesn't fit the tabular content model the way a module's attributes do, and one
    section can be referenced by many attributes). Instead, each attribute node keeps its
    `<attr>_section_refs` list (added by `DOMTableSpecParser`'s `ref_columns`), and resolved
    SpecModel section models are returned separately and, if a SectionRegistry is provided, shared
    across modules.

    Sections are resolved lazily: only ids actually found in `<attr>_section_refs` (or, recursively,
    in a resolved section's own `section_refs`) trigger a section build. A section's own outgoing
    references are followed to the same depth, guarded against cycles.
    """

    def __init__(
        self,
        module_factory: Optional[SpecFactory] = None,
        section_factory: Optional[SpecFactory] = None,
        section_registry: Optional[SectionRegistry] = None,
        ref_columns: Optional[List[int]] = None,
        doc_handler: Optional[DocHandler] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the ModuleSpecBuilder.

        Args:
            module_factory (Optional[SpecFactory]): Factory for building the module attribute model.
                If None, uses a default SpecFactory.
            section_factory (Optional[SpecFactory]): Factory for building section models. If None,
                uses a SpecFactory configured with SectionSpecParser as its table_parser.
            section_registry (Optional[SectionRegistry]): Registry for sharing section models by
                section_id across modules. If None, sections are still resolved and returned, but
                not shared or reused across separate ModuleSpecBuilder calls.
            ref_columns (Optional[List[int]]): Column indices to scan for section references,
                passed to DOMTableSpecParser as `parser_kwargs={"ref_columns": ref_columns}` when
                building the module model. If None, no columns are scanned and no sections are
                resolved.
            doc_handler (Optional[DocHandler]): Handler used to download referenced images. If None,
                a default DocHandler is used (only its generic `download` method is needed).
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is
                created.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.module_factory = module_factory or SpecFactory(logger=self.logger)
        self.section_factory = section_factory or SpecFactory(
            table_parser=SectionSpecParser(logger=self.logger), logger=self.logger
        )
        self.section_registry = section_registry
        self.ref_columns = ref_columns
        self.doc_handler = doc_handler or DocHandler(config=self.section_factory.config, logger=self.logger)

    def build_from_url(
        self,
        url: str,
        cache_file_name: str,
        table_id: str,
        force_download: bool = False,
        progress_observer: Optional[ProgressObserver] = None,
        json_file_name: Optional[str] = None,
    ) -> Tuple[SpecModel, Dict[str, SpecModel]]:
        """Download (if needed), parse, and cache a module model, resolving its explanatory sections.

        Args:
            url (str): The URL to download the module's document from.
            cache_file_name (str): Filename of the cached input document.
            table_id (str): The id of the module attribute table to parse.
            force_download (bool): If True, always download the input file even if cached.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download
                and parsing progress for the module table. Section resolution does not report
                progress.
            json_file_name (Optional[str]): Filename to save the cached module model as. Each
                resolved section is cached separately (see `build_from_dom`).

        Returns:
            Tuple[SpecModel, Dict[str, SpecModel]]: The module model, and a dict mapping section_id
                to SpecModel for every section resolved (directly or transitively) from it.

        """
        self.module_factory.input_handler.cache_file_name = cache_file_name
        dom = self.module_factory.load_document(
            url=url,
            cache_file_name=cache_file_name,
            force_download=force_download,
            progress_observer=progress_observer,
        )
        return self.build_from_dom(
            dom, table_id=table_id, url=url, json_file_name=json_file_name, progress_observer=progress_observer
        )

    def build_from_dom(
        self,
        dom: BeautifulSoup,
        table_id: str,
        url: str,
        json_file_name: Optional[str] = None,
        progress_observer: Optional[ProgressObserver] = None,
    ) -> Tuple[SpecModel, Dict[str, SpecModel]]:
        """Build a module model from an already-loaded DOM, resolving its explanatory sections.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object, already loaded (e.g. by a caller that
                also needs it for other tables, such as IODSpecBuilder).
            table_id (str): The id of the module attribute table to parse.
            url (str): The URL the DOM was loaded from, used to resolve relative image paths within
                referenced sections and recorded in each model's metadata.
            json_file_name (Optional[str]): Filename to save the cached module model as.
            progress_observer (Optional[ProgressObserver]): Optional observer to report parsing
                progress for the module table. Section resolution does not report progress.

        Returns:
            Tuple[SpecModel, Dict[str, SpecModel]]: The module model, and a dict mapping section_id
                to SpecModel for every section resolved (directly or transitively) from it.

        """
        module_model = self.module_factory.build_model(
            doc_object=dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            progress_observer=progress_observer,
            parser_kwargs={"ref_columns": self.ref_columns},
        )
        section_models = self._resolve_sections(module_model.content, dom, url)
        return module_model, section_models

    def _resolve_sections(self, content: Node, dom: BeautifulSoup, url: str) -> Dict[str, SpecModel]:
        """Resolve every section referenced (directly or transitively) from a content tree."""
        section_models: Dict[str, SpecModel] = {}
        visited_sections: set = set()
        for node in PreOrderIter(content):
            for section_id in self._collect_section_refs(node):
                self._resolve_section(section_id, dom, url, visited_sections, section_models)
        return section_models

    def _resolve_section(
        self,
        section_id: str,
        dom: BeautifulSoup,
        url: str,
        visited_sections: set,
        section_models: Dict[str, SpecModel],
    ) -> None:
        """Resolve one section (and, recursively, any section it references) into section_models."""
        if section_id in section_models:
            return
        if self.section_registry is not None and section_id in self.section_registry:
            section_models[section_id] = self.section_registry[section_id]
            return
        if section_id in visited_sections:
            self.logger.warning(f"Circular section reference detected for '{section_id}', not recursing further.")
            return

        with self._visit_section(section_id, visited_sections):
            try:
                section_model = self.section_factory.build_model(
                    doc_object=dom,
                    table_id=section_id,
                    url=url,
                    json_file_name=f"{section_id}.json",
                )
            except ValueError as e:
                self.logger.warning(f"Could not resolve section '{section_id}': {e}")
                return

            self._resolve_section_images(section_model, url)

            # Recurse into this section's own outgoing references before registering it, so that
            # a cycle back to a section still being resolved is caught by visited_sections below
            # instead of silently short-circuiting on the section_models check above.
            for node in PreOrderIter(section_model.content):
                for nested_section_id in self._collect_section_refs(node):
                    self._resolve_section(nested_section_id, dom, url, visited_sections, section_models)

            section_models[section_id] = section_model
            if self.section_registry is not None:
                self.section_registry[section_id] = section_model

    @contextmanager
    def _visit_section(self, section_id: str, visited_sections: set) -> Any:
        """Context manager to temporarily add a section_id to visited_sections during recursion."""
        visited_sections.add(section_id)
        try:
            yield
        finally:
            visited_sections.remove(section_id)

    def _collect_section_refs(self, node: Node) -> List[str]:
        """Return every section id listed in any of a node's `*section_refs` attributes."""
        section_refs = []
        for attr_name, value in vars(node).items():
            if attr_name.endswith("section_refs") and isinstance(value, list):
                section_refs.extend(value)
        return section_refs

    def _resolve_section_images(self, section_model: SpecModel, url: str) -> None:
        """Download (if not already cached) and record the local path for each image block's source."""
        for node in PreOrderIter(section_model.content):
            image_src = getattr(node, "image_src", None)
            if not image_src or getattr(node, "image_path", None):
                continue
            image_path = os.path.join("figures", os.path.basename(image_src))
            file_path = os.path.join(
                self.section_factory.config.get_param("cache_dir"), "standard", image_path
            )
            try:
                if not os.path.exists(file_path):
                    self.doc_handler.download(urljoin(url, image_src), file_path, binary=True)
                node.image_path = image_path
            except RuntimeError as e:
                self.logger.warning(f"Failed to download image '{image_src}': {e}")
