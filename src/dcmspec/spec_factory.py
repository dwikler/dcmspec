"""Factory for DICOM specification model creation in dcmspec.

Provides the SpecFactory class, which orchestrates downloading, parsing, and caching
of DICOM specification tables from standard sources, producing structured SpecModel objects.
"""
import logging
import os
from typing import Any, Optional, Dict, Type
# BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
from dcmspec.progress import Progress, ProgressStatus, add_progress_step, handle_legacy_callback, offset_progress_steps
from typing import Callable
# END LEGACY SUPPORT
from dcmspec.config import Config
from dcmspec.progress import ProgressObserver
from dcmspec.spec_model import SpecModel
from dcmspec.doc_handler import DocHandler
from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.dom_table_spec_parser import DOMTableSpecParser
from dcmspec.spec_parser import SpecParser
from dcmspec.spec_store import SpecStore
from dcmspec.xhtml_doc_handler import XHTMLDocHandler


class SpecFactory:
    """Factory for DICOM specification models.

    Orchestrates the end-to-end process of producing structured SpecModel objects from DICOM specification sources.
    This includes coordinating input handlers for downloading and caching files, table parsers for extracting
    structured data into SpecModel objects, and model stores for caching and loading models.
    Supports flexible configuration and caching strategies.

    Typical usage:
        ```python
        factory = SpecFactory(...)
        model = factory.create_model(...)
        ```
        
    """

    def __init__(
        self,
        input_handler: Optional[DocHandler] = None,
        model_class: Optional[Type[SpecModel]] = None,
        model_store: Optional[SpecStore] = None,
        table_parser: Optional[SpecParser] = None,
        column_to_attr: Optional[Dict[int, str]] = None,
        name_attr: Optional[str] = None,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
        parser_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the SpecFactory.

        The default values for `column_to_attr` and `name_attr` are designed for parsing
        DICOM PS3.3 module attribute tables, where columns typically represent element name,
        tag, type, and description.

        Args:
            input_handler (Optional[DocHandler]): Handler for downloading and parsing input files.
                If None, a default XHTMLDocHandler is used.
            model_class (Optional[Type[SpecModel]]): The class to instantiate for the model.
                If None, defaults to SpecModel.
            model_store (Optional[SpecStore]): Store for loading and saving models.
                If None, a default JSONSpecStore is used.
            table_parser (Optional[SpecParser]): Parser for extracting tables from documents.
                If None, a default DOMTableSpecParser is used.
            column_to_attr (Optional[Dict[int, str]]): Mapping from column indices to names of attributes
                of model nodes. If None, a default mapping is used.
            name_attr (Optional[str]): Attribute name to use for node names in the model.
                If None, defaults to "elem_name".
            config (Optional[Config]): Configuration object. If None, a default Config is created.
            logger (Optional[logging.Logger]): Logger instance to use.
                If None, a default logger is created.
            parser_kwargs (Optional[Dict[str, Any]]): Default keyword arguments to pass to the parser's
                `parse` method. Use this to supply parser-specific options such as `skip_columns` or `unformatted`.

        Raises:
            TypeError: If config is not a Config instance or None.

        Note:
            `column_to_attr` and related flags (such as `unformatted`) are dicts to support non-sequential
            column mappings.

        """
        import logging
        if config is not None and not isinstance(config, Config):
            raise TypeError("config must be an instance of Config or None")
        self.config = config or Config()

        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.model_class = model_class or SpecModel
        self.input_handler = input_handler or XHTMLDocHandler(config=self.config, logger=self.logger)
        self.model_store = model_store or JSONSpecStore(logger=self.logger)
        self.table_parser = table_parser or DOMTableSpecParser(logger=self.logger)
        self.column_to_attr = column_to_attr or {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}
        self.name_attr = name_attr or "elem_name"
        self.parser_kwargs = parser_kwargs or {}

    def load_document(self, 
                    url: str, 
                    cache_file_name: str, 
                    force_download: bool = False, 
                    progress_observer: 'Optional[ProgressObserver]' = None,
                    # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
                    progress_callback: 'Optional[Callable[[int], None]]' = None,
                    # END LEGACY SUPPORT
                    ) -> Any:
        """Download, cache, and parse the specification file from a URL, returning the document object.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            force_download (bool): If True, always download the input file even if cached.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY] Optional callback to report progress
                Deprecated: use progress_observer instead. Will be removed in a future release.

        Returns:
            Any: The document object.

        Note:
            Progress reporting via progress_observer is delegated to the input handler (e.g., XHTMLDocHandler,
            PDFDocHandler) and typically covers only downloading and caching (writing to disk).
            Parsing and model building do not emit progress updates.

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        # This will download if needed and always parse/return the DOM
        return self.input_handler.load_document(cache_file_name=cache_file_name,
                                                url=url,
                                                force_download=force_download,
                                                progress_observer=progress_observer
                                                )

    def try_load_cache(
        self,
        json_file_name: Optional[str],
        include_depth: Optional[int],
        model_kwargs: Optional[Dict[str, Any]],
        force_parse: bool = False,
    ) -> Optional[SpecModel]:
        """Check for and load a model from cache if available and not force_parse."""
        if json_file_name is None:
            cache_file_name = getattr(self.input_handler, "cache_file_name", None)
            if cache_file_name is None:
                raise ValueError("input_handler.cache_file_name not set")
            json_file_name = f"{os.path.splitext(cache_file_name)[0]}.json"
        json_file_path = os.path.join(self.config.get_param("cache_dir"), "model", json_file_name)
        if os.path.exists(json_file_path) and not force_parse:
            model = self._load_model_from_cache(json_file_path, include_depth, model_kwargs)
            if model is not None:
                return model
        return None

    def build_model(
        self,
        doc_object: Any,
        table_id: Optional[str] = None,
        url: Optional[str] = None,
        json_file_name: Optional[str] = None,
        include_depth: Optional[int] = None,
        progress_observer: Optional[ProgressObserver] = None,
        force_parse: bool = False,
        model_kwargs: Optional[Dict[str, Any]] = None,
        parser_kwargs: Optional[Dict[str, Any]] = None,
    ) -> SpecModel:
        """Build and cache a DICOM specification model from a parsed document object.

        Args:
            doc_object (Any): The parsed document object to be parsed into a model.
                - For XHTML: a BeautifulSoup DOM object.
                - For PDF: a grouped table dict (from PDFDocHandler).
                - For other formats: as defined by the handler/parser.
            table_id (Optional[str]): Table identifier for model parsing.
            url (Optional[str]): The URL the document was fetched from (for metadata).
            json_file_name (Optional[str]): Filename to save the cached JSON model.
            include_depth (Optional[int]): The depth to which included tables should be parsed.
            force_parse (bool): If True, always parse and (over)write the JSON cache file.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
                See the Note below for details on the progress events and their properties.
            model_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments for model construction.
                Use this to supply extra parameters required by custom SpecModel subclasses.
                For example, if your model class is `MyModel(metadata, content, foo, bar)`, pass
                `model_kwargs={"foo": foo_value, "bar": bar_value}`.
            parser_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments to pass to the parser's
                `parse` method. Use this to supply parser-specific options such as `skip_columns`.

        If `json_file_name` is not provided, the factory will attempt to use
        `self.input_handler.cache_file_name` to generate a default JSON file name.
        If neither is set, a ValueError is raised.

        Returns:
            SpecModel: The constructed model.

        Note:
            The type of `doc_object` depends on the handler/parser used:
            - For XHTML: a BeautifulSoup DOM object.
            - For PDF: a grouped table dict as returned by PDFDocHandler.
            - For other formats: as defined by the handler/parser.

        Note:
            If a progress observer accepting a Progress object is provided, progress events are as follows:

            - **Step 1 (PARSING_TABLE):** Events include `status=PARSING_TABLE`, `step=1`, `total_steps=2`,
                and a meaningful `percent` value.
            - **Step 2 (SAVING_MODEL):** Events include `status=SAVING_MODEL`, `step=2`, `total_steps=2`,
                and `percent` values of `0` (start) and `100` (completion).

            For example usage in a client application,
            see [`ProgressStatus`](progress.md#dcmspec.progress.ProgressStatus).
            
        """
        # Try to load from cache first
        model = self.try_load_cache(json_file_name, include_depth, model_kwargs, force_parse)
        if model is not None:
            return model

        # Enrich the progress observer for parsing step
        if progress_observer:
            @add_progress_step(step=1, total_steps=2, status=ProgressStatus.PARSING_TABLE)
            def parsing_progress_observer(progress):
                progress_observer(progress)
        else:
            parsing_progress_observer = None

        # Parse provided document otherwise
        merged_parser_kwargs = {**self.parser_kwargs, **(parser_kwargs or {})}
        model = self._parse_and_build_model(
            doc_object=doc_object,
            table_id=table_id,
            url=url,
            include_depth=include_depth,
            model_kwargs=model_kwargs,
            parser_kwargs=merged_parser_kwargs,
            progress_observer=parsing_progress_observer,
        )

        # Cache the newly built model if requested
        if json_file_name:
            json_file_path = os.path.join(self.config.get_param("cache_dir"), "model", json_file_name)
            try:
                if progress_observer:
                    # Report start of saving
                    progress_observer(Progress(0, status=ProgressStatus.SAVING_MODEL, step=2, total_steps=2))
                self.model_store.save(model, json_file_path)
                if progress_observer:
                    # Report completion of saving
                    progress_observer(Progress(100, status=ProgressStatus.SAVING_MODEL, step=2, total_steps=2))

            except Exception as e:
                self.logger.warning(f"Failed to cache model to {json_file_path}: {e}")

        return model

    def create_model(
        self,
        url: str,
        cache_file_name: str,
        table_id: Optional[str] = None,
        force_parse: bool = False,
        force_download: bool = False,
        json_file_name: Optional[str] = None,
        include_depth: Optional[int] = None,
        progress_observer: Optional[ProgressObserver] = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: Optional[Callable[[int], None]] = None,
        # END LEGACY SUPPORT
        handler_kwargs: Optional[Dict[str, Any]] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
        parser_kwargs: Optional[Dict[str, Any]] = None,
    ) -> SpecModel:
        """Integrated, one-step method to fetch, parse, and build a DICOM specification model from a URL.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            table_id (Optional[str]): Table identifier for model parsing.
            force_parse (bool): If True, always parse the DOM and generate the JSON model, even if cached.
            force_download (bool): If True, always download the input file and generate the model even if cached.
                Note: force_download also implies force_parse.
            json_file_name (Optional[str]): Filename to save the cached JSON model.
            include_depth (Optional[int]): The depth to which included tables should be parsed.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
                See the Note below for details on the progress events and their properties.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.
            handler_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments for the input handler's methods.
            model_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments for model construction.
                Use this to supply extra parameters required by custom SpecModel subclasses.
                For example, if your model class is `MyModel(metadata, content, foo, bar)`, pass
                `model_kwargs={"foo": foo_value, "bar": bar_value}`.
            parser_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments to pass to the parser's
                `parse` method. Use this to supply parser-specific options such as `skip_columns`.

        Returns:
            SpecModel: The constructed model.

            
        Note:
            If a progress observer accepting a Progress object is provided, progress events are as follows:

            - **Step 1 (DOWNLOADING):** Events include `status=DOWNLOADING`, `step=1`, `total_steps=3`,
                and a meaningful `percent` value.
            - **Step 2 (PARSING_TABLE):** Events include `status=PARSING_TABLE`, `step=2`, `total_steps=3`,
                and a meaningful `percent` value.
            - **Step 3 (SAVING_MODEL):** Events include `status=SAVING_MODEL`, `step=3`, `total_steps=3`,
                and `percent` values of `0` (start) and `100` (completion).

            For example usage in a client application,
            see [`ProgressStatus`](progress.md#dcmspec.progress.ProgressStatus).

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        # Set cache_file_name on the handler before checking cache
        self.input_handler.cache_file_name = cache_file_name

        # Try to load from cache before loading document object
        model = self.try_load_cache(json_file_name, include_depth, model_kwargs, force_parse or force_download)
        if model is not None:
            return model

        # --- Step 1 (DOWNLOADING)

        # Wrap progress observer for step 1
        if progress_observer:
            @add_progress_step(step=1, total_steps=3)
            def load_progress_observer(progress):
                progress_observer(progress)
        else:
            load_progress_observer = None

        # Pass handler_kwargs to load_document
        doc_object = self.input_handler.load_document(
            cache_file_name=cache_file_name,
            url=url,
            force_download=force_download,
            progress_observer=load_progress_observer,
            # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
            progress_callback=progress_callback,
            # END LEGACY SUPPORT
            **(handler_kwargs or {})
        )

        # --- Step 2 and 3 (PARSING_TABLE and SAVING_MODEL)

        # Wrap progress observer for step 2 and 3
        if progress_observer:
            @offset_progress_steps(step_offset=1, total_steps=3)
            def build_progress_observer(progress):
                progress_observer(progress)
        else:
            build_progress_observer = None
            
        return self.build_model(
            doc_object=doc_object,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            include_depth=include_depth,
            progress_observer=build_progress_observer,
            force_parse=force_parse or force_download,
            model_kwargs=model_kwargs,
            parser_kwargs=parser_kwargs,
        )


    def _load_model_from_cache(
        self,
        json_file_path: str,
        include_depth: Optional[int],
        model_kwargs: Optional[Dict[str, Any]],
    ) -> Optional[SpecModel]:
        """Load model from cache file if include depth is valid."""
        try:
            # Load the model from cache
            model = self.model_store.load(json_file_path)
            self.logger.info(f"Loaded model from cache {json_file_path}")

            # Do not use cache if include_depth does not match the cached model's metadata
            cached_depth = getattr(model.metadata, "include_depth", None)
            if (
                (include_depth is not None and cached_depth is not None and int(cached_depth) != int(include_depth))
                or (include_depth is None and cached_depth is not None)
                or (include_depth is not None and cached_depth is None)
            ):
                self.logger.info(
                    (
                        f"Cached model include_depth ({cached_depth}) "
                        f"does not match requested ({include_depth}), reparsing."
                    )
                )
                return None

            # Return the cached model, reconstructing it to the required subclass if necessary        
            if isinstance(model, self.model_class):
                model.logger = self.logger
                return model
            return self.model_class(
                metadata=model.metadata,
                content=model.content,
                logger=self.logger,
                **(model_kwargs or {}),
            )

        except Exception as e:
            self.logger.warning(f"Failed to load model from cache {json_file_path}: {e}")
            return None

    def _parse_and_build_model(
        self,
        doc_object: Any,
        table_id: Optional[str],
        url: Optional[str],
        include_depth: Optional[int],
        model_kwargs: Optional[Dict[str, Any]],
        parser_kwargs: Optional[Dict[str, Any]] = None,
        progress_observer: Optional[ProgressObserver] = None,
    ) -> SpecModel:
        """Parse and Build model from provided parsed document object."""
        # Parse content and some metadata from the parsed document object
        metadata, content = self.table_parser.parse(
            doc_object,
            table_id=table_id,
            include_depth=include_depth,
            column_to_attr=self.column_to_attr,
            progress_observer=progress_observer,
            name_attr=self.name_attr,
            **(parser_kwargs or {}),
        )

        # Add args values to model metadata
        metadata.url = url

        # Build the model from parsed content and metadata
        model = self.model_class(
            metadata=metadata,
            content=content,
            logger=self.logger,
            **(model_kwargs or {}),
        )

        # Clean up model from title nodes
        model.exclude_titles()

        return model