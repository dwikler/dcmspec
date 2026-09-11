"""Builder for DICOM module attribute models with resolved explanatory sections in dcmspec.

This module provides the ModuleSpecBuilder class, which builds a module attribute model and
resolves the DICOM Part 3 sections its attributes directly reference (e.g. "See Section
C.7.6.16.2.2.1" in an attribute's description), caching each section separately and sharing
them across modules via a SectionRegistry.
"""
import logging
from typing import Dict, List, Optional, Tuple

from anytree import Node, PreOrderIter
from bs4 import BeautifulSoup

from dcmspec.doc_handler import DocHandler
from dcmspec.progress import ProgressObserver
from dcmspec.section_registry import SectionRegistry
from dcmspec.dom_section_spec_parser import DOMSectionSpecParser
from dcmspec.section_image_resolver import SectionImageResolver
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_model import SpecModel


class ModuleSpecBuilder:
    """Builds a module attribute model, resolving the sections its attributes directly reference.

    Sections are found via "See Section C.x" references in the Description column and cached
    as separate SpecModels, one JSON file per section. A resolved section's own outgoing
    references are left on its metadata, not resolved further -- a caller wanting to go deeper
    can resolve individual ids itself the same way. A SectionRegistry, if provided, lets modules
    reuse an already-resolved section.
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
                uses a SpecFactory configured with DOMSectionSpecParser as its table_parser.
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
            table_parser=DOMSectionSpecParser(logger=self.logger), logger=self.logger
        )
        self.section_registry = section_registry
        self.ref_columns = ref_columns
        self.doc_handler = doc_handler or DocHandler(config=self.section_factory.config, logger=self.logger)
        self.image_resolver = SectionImageResolver(
            doc_handler=self.doc_handler,
            cache_dir=self.section_factory.config.get_param("cache_dir"),
            logger=self.logger,
        )

    def build_from_url(
        self,
        url: str,
        cache_file_name: str,
        table_id: str,
        force_download: bool = False,
        progress_observer: Optional[ProgressObserver] = None,
        json_file_name: Optional[str] = None,
    ) -> Tuple[SpecModel, Dict[str, SpecModel]]:
        """Download (if needed), parse, and cache a module model, resolving its referenced sections.

        Args:
            url (str): The URL to download the module's document from.
            cache_file_name (str): Filename of the cached input document.
            table_id (str): The id of the module attribute table to parse.
            force_download (bool): If True, always download the input file even if cached, re-parse
                the module table instead of reusing its cached model, and re-download (rather than
                reuse) each resolved section's cached images.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download
                and parsing progress for the module table. Section resolution does not report
                progress.
            json_file_name (Optional[str]): Filename to save the cached module model as. Each
                resolved section is cached separately (see `build_from_dom`).

        Returns:
            Tuple[SpecModel, Dict[str, SpecModel]]: The module model, and a dict mapping section_id
                to SpecModel for every section directly referenced from it.

        """
        self.module_factory.input_handler.cache_file_name = cache_file_name
        dom = self.module_factory.load_document(
            url=url,
            cache_file_name=cache_file_name,
            force_download=force_download,
            progress_observer=progress_observer,
        )
        return self.build_from_dom(
            dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            progress_observer=progress_observer,
            force_download=force_download,
        )

    def build_from_dom(
        self,
        dom: BeautifulSoup,
        table_id: str,
        url: str,
        json_file_name: Optional[str] = None,
        progress_observer: Optional[ProgressObserver] = None,
        force_download: bool = False,
    ) -> Tuple[SpecModel, Dict[str, SpecModel]]:
        """Build a module model from an already-loaded DOM, resolving its referenced sections.

        Args:
            dom (BeautifulSoup): The parsed XHTML DOM object, already loaded (e.g. by a caller that
                also needs it for other tables, such as IODSpecBuilder).
            table_id (str): The id of the module attribute table to parse.
            url (str): The URL the DOM was loaded from, used to resolve relative image paths within
                referenced sections and recorded in each model's metadata.
            json_file_name (Optional[str]): Filename to save the cached module model as.
            progress_observer (Optional[ProgressObserver]): Optional observer to report parsing
                progress for the module table. Section resolution does not report progress.
            force_download (bool): If True, re-parse the module table instead of reusing its
                cached model, and re-download (rather than reuse) each resolved section's
                cached images.

        Returns:
            Tuple[SpecModel, Dict[str, SpecModel]]: The module model, and a dict mapping section_id
                to SpecModel for every section directly referenced from it.

        """
        module_model = self.module_factory.build_model(
            doc_object=dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            progress_observer=progress_observer,
            force_parse=force_download,
            parser_kwargs={"ref_columns": self.ref_columns},
        )
        section_models = self._resolve_sections(module_model.content, dom, url, force_download)
        return module_model, section_models

    def _resolve_sections(
        self, content: Node, dom: BeautifulSoup, url: str, force_download: bool
    ) -> Dict[str, SpecModel]:
        """Resolve every section directly referenced from a content tree."""
        section_models: Dict[str, SpecModel] = {}
        for node in PreOrderIter(content):
            for section_id in self._collect_section_refs(node):
                self._resolve_section(section_id, dom, url, section_models, force_download)
        return section_models

    def _resolve_section(
        self,
        section_id: str,
        dom: BeautifulSoup,
        url: str,
        section_models: Dict[str, SpecModel],
        force_download: bool,
    ) -> None:
        """Resolve one section into section_models. Does not resolve sections it references in turn."""
        if section_id in section_models:
            return
        if self.section_registry is not None and section_id in self.section_registry:
            section_models[section_id] = self.section_registry[section_id]
            return

        try:
            section_model = self.section_factory.build_model(
                doc_object=dom,
                table_id=section_id,
                url=url,
                json_file_name=f"sections/{section_id}.json",
            )
        except ValueError as e:
            self.logger.warning(f"Could not resolve section '{section_id}': {e}")
            return

        self.image_resolver.resolve(section_model, url, force_download=force_download)

        section_models[section_id] = section_model
        if self.section_registry is not None:
            self.section_registry[section_id] = section_model

    def _collect_section_refs(self, node: Node) -> List[str]:
        """Return every section id listed in any of a node's `*section_refs` attributes."""
        section_refs = []
        for attr_name, value in vars(node).items():
            if attr_name.endswith("section_refs") and isinstance(value, list):
                section_refs.extend(value)
        return section_refs
