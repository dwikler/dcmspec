"""Factory for DICOM specification model creation in dcmspec.

Provides the SpecFactory class, which orchestrates downloading, parsing, and caching
of DICOM specification tables from standard sources, producing structured SpecModel objects.
"""
import logging
import os
from typing import Optional, Dict

from dcmspec.config import Config
from dcmspec.spec_model import SpecModel
from dcmspec.doc_handler import DocHandler
from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.dom_table_spec_parser import DOMTableSpecParser
from dcmspec.spec_parser import SpecParser
from dcmspec.spec_store import SpecStore
from dcmspec.xhtml_doc_handler import XHTMLDocHandler


class SpecFactory:
    """Factory for DICOM specification models.

    Coordinates the downloading, parsing, and caching of DICOM specification tables.
    Uses input handlers, table parsers, and model stores to produce SpecModel objects
    from URLs or cached files. Supports flexible configuration and caching strategies.

    Typical usage:
        factory = SpecFactory(...)
        model = factory.create_model(...)
    """

    def __init__(
        self,
        input_handler: Optional[DocHandler] = None,
        model_class: Optional[SpecModel] = None,
        model_store: Optional[SpecStore] = None,
        table_parser: Optional[SpecParser] = None,
        column_to_attr: Dict[int, str] = None,
        name_attr: str = None,
        config: Optional[Config] = None,
        logger: Optional["logging.Logger"] = None,
    ):
        """Initialize the SpecFactory.

        The default values for `column_to_attr` and `name_attr` are designed for parsing
        DICOM PS3.3 module attribute tables, where columns typically represent element name,
        tag, type, and description.

        Args:
            model_class (Optional[type]): The class to instantiate for the model (must be a subclass of SpecModel).
                If None, defaults to SpecModel.
            input_handler (Optional[DocHandler]): Handler for downloading and parsing input files.
                If None, a default XHTMLDocHandler is used.
            model_store (Optional[SpecStore]): Store for loading and saving models.
                If None, a default JSONSpecStore is used.
            table_parser (Optional[SpecParser]): Parser for extracting tables from documents.
                If None, a default DOMTableSpecParser is used.
            column_to_attr (Dict[int, str], optional): Mapping from column indices to names of attributes
                of model nodes. If None, a default mapping is used.
            name_attr (str, optional): Attribute name to use for node names in the model.
                If None, defaults to "elem_name".
            config (Optional[Config]): Configuration object. If None, a default Config is created.
            logger (Optional[logging.Logger]): Logger instance to use.
                If None, a default logger is created.

        Raises:
            TypeError: If config is not a Config instance or None.

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

    def load_dom(self, url: str, cache_file_name: str, force_download: bool = False):
        """Download, cache, and parse the specification file from a URL, returning the DOM.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            force_download (bool): If True, always download the input file even if cached.

        Returns:
            object: The parsed DOM (e.g., BeautifulSoup object).

        """
        # This will download if needed and always parse/return the DOM
        return self.input_handler.get_dom(cache_file_name=cache_file_name, url=url, force_download=force_download)


    def build_model(
        self,
        dom,
        table_id: Optional[str] = None,
        url: Optional[str] = None,
        json_file_name: Optional[str] = None,
        include_depth: Optional[int] = None,
        force_parse: bool = False,
        model_kwargs: Optional[dict] = None,
    ) -> SpecModel:
        """Build and cache a DICOM specification model from a parsed DOM.

        Args:
            dom: The parsed DOM object (e.g., BeautifulSoup).
            table_id (Optional[str]): Table identifier for model parsing.
            url (Optional[str]): The URL the DOM was fetched from (for metadata).
            json_file_name (Optional[str]): Filename to save the cached JSON model.
            include_depth (Optional[int]): The depth to which included tables should be parsed.
            force_parse (bool): If True, always parse and (over)write the JSON cache file.
            model_kwargs (Optional[dict]): Additional keyword arguments for model construction.

        If `json_file_name` is not provided, the factory will attempt to use
        `self.input_handler.cache_file_name` to generate a default JSON file name.
        If neither is set, a ValueError is raised.

        Returns:
            SpecModel: The constructed model.

        """
        if json_file_name is None:
            cache_file_name = getattr(self.input_handler, "cache_file_name", None)
            if cache_file_name is None:
                raise ValueError("input_handler.cache_file_name not set")
            json_file_name = f"{os.path.splitext(cache_file_name)[0]}.json"
        json_file_path = os.path.join(self.config.get_param("cache_dir"), "model", json_file_name)

        if os.path.exists(json_file_path) and not force_parse:
            try:
                model = self.model_store.load(json_file_path)
                self.logger.info(f"Loaded model from cache {json_file_path}")
                # Check if include_depth matches the cached model's metadata
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
                    # Fallback to parsing: do not return cached model
                else:
                    if isinstance(model, self.model_class):
                        return model
                    model = self.model_class(
                        metadata=model.metadata,
                        content=model.content,
                        **(model_kwargs or {}),
                    )
                    return model
            except Exception as e:
                self.logger.warning(f"Failed to load model from cache {json_file_path}: {e}")
                # Fallback to parsing

        metadata, content = self.table_parser.parse(
            dom,
            table_id=table_id,
            include_depth=include_depth,
            column_to_attr=self.column_to_attr,
            name_attr=self.name_attr,
        )
        # Complete metadata
        metadata.url = url
        metadata.table_id = table_id
        # Store include_depth as int if not None, else omit from metadata
        if include_depth is not None:
            metadata.include_depth = int(include_depth)
        metadata.column_to_attr = self.column_to_attr
        metadata.name_attr = self.name_attr

        model = self.model_class(
            metadata=metadata,
            content=content,
            **(model_kwargs or {}),
        )

        model.exclude_titles()

        if json_file_name:
            try:
                self.model_store.save(model, json_file_path)
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
        model_kwargs: Optional[dict] = None,
    ) -> SpecModel:
        """Integrated, one-step method to fetch, parse, and build a DICOM specification model from a URL.

        Args:
            url (str): The URL to download the input file from.
            cache_file_name (str): Filename of the cached input file.
            table_id (Optional[str]): Table identifier for model parsing.
            force_parse (bool): If True, always parse the DOM and generate the JSON model, even if cached.
            force_download (bool): If True, always download the input file and generate the model even if cached.
            json_file_name (Optional[str]): Filename to save the cached JSON model.
            include_depth (Optional[int]): The depth to which included tables should be parsed.
            model_kwargs (Optional[dict]): Additional keyword arguments for model construction.

        Returns:
            SpecModel: The constructed model.

        """
        dom = self.load_dom(url=url, cache_file_name=cache_file_name, force_download=force_download)
        return self.build_model(
            dom=dom,
            table_id=table_id,
            url=url,
            json_file_name=json_file_name,
            include_depth=include_depth,
            force_parse=force_parse or force_download,
            model_kwargs=model_kwargs,
        )



