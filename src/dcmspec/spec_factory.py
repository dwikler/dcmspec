"""Factory for DICOM specification model creation in dcmspec.

Provides the SpecFactory class, which orchestrates downloading, parsing, and caching
of DICOM specification tables from standard sources, producing structured SpecModel objects.
"""
import os
from typing import Optional, Dict

from dcmspec.config import Config
from dcmspec.spec_model import SpecModel
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.dom_table_spec_parser import DOMTableSpecParser


class SpecFactory:
    """Factory for DICOM specification models.

    Coordinates the downloading, parsing, and caching of DICOM specification tables.
    Uses input handlers, table parsers, and model stores to produce SpecModel objects
    from URLs or cached files. Supports flexible configuration and caching strategies.

    Typical usage:
        factory = SpecFactory(...)
        model = factory.from_url(...)
    """

    def __init__(
        self,
        input_handler: Optional[XHTMLDocHandler] = None,
        model_store: Optional[JSONSpecStore] = None,
        table_parser: Optional[DOMTableSpecParser] = None,
        column_to_attr: Dict[int, str] = None,
        name_attr: str = None,
        config: Optional[Config] = None,
    ):
        """Initialize the SpecFactory.

        The default values for `column_to_attr` and `name_attr` are designed for parsing
        DICOM PS3.3 module attribute tables, where columns typically represent element name,
        tag, type, and description.

        Args:
            input_handler (Optional[XHTMLDocHandler]): Handler for downloading and parsing input files.
                If None, a default XHTMLDocHandler is used.
            model_store (Optional[JSONSpecStore]): Store for loading and saving models.
                If None, a default JSONSpecStore is used.
            table_parser (Optional[DOMTableSpecParser]): Parser for extracting tables from documents.
                If None, a default DOMTableSpecParser is used.
            column_to_attr (Dict[int, str], optional): Mapping from column indices to names of attributes
                of model nodes. If None, a default mapping is used.
            name_attr (str, optional): Attribute name to use for node names in the model.
                If None, defaults to "elem_name".
            config (Optional[Config]): Configuration object. If None, a default Config is created.

        Raises:
            TypeError: If config is not a Config instance or None.

        """
        if config is not None and not isinstance(config, Config):
            raise TypeError("config must be an instance of Config or None")
        self.config = config or Config()

        self.input_handler = input_handler or XHTMLDocHandler(config=self.config)
        self.model_store = model_store or JSONSpecStore()
        self.table_parser = table_parser or DOMTableSpecParser()
        self.column_to_attr = column_to_attr or {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}
        self.name_attr = name_attr or "elem_name"

    def from_url(
        self,
        url: str,
        cache_file_name: str,
        table_id: Optional[str] = None,
        force_download: bool = False,
        json_file_name: Optional[str] = None,
        **kwargs,
    ) -> SpecModel:
        """Create and cache a DICOM specification model from a URL.

        Downloads (if needed) and parses an input file from a URL, creates the DICOMAttributeModel,
        and caches the result as JSON. This method orchestrates the full workflow: downloading
        (or using a cached file), parsing the DICOM specification table, constructing the model,
        and saving it as a JSON file for future use.

        Args:
            url: The URL to download the input file from.
            cache_file_name: filename of the cached input file.
            table_id: Optional table identifier for model parsing.
            force_download: If True, always download the input file and generate the model even if cached.
            json_file_name: Optional filename to save the cached JSON model.
            **kwargs: Additional arguments for model construction.

        Returns:
            DICOMAttributeModel: The constructed model.

        """
        json_file_name = (
            json_file_name or f"{os.path.splitext(cache_file_name)[0]}.json"
        )
        json_file_path = os.path.join(self.config.get_param("cache_dir"), "model", json_file_name)
        if os.path.exists(json_file_path) and not force_download:
            try:
                model = self.model_store.load(json_file_path)
                print(f"Loaded model from cache {json_file_path}")
                model = SpecModel(
                    metadata=model.metadata,
                    content=model.content,
                    **kwargs,
                )
                return model
            except Exception as e:
                print(f"Warning: Failed to load model from cache {json_file_path}: {e}")
                # Fallback to input file

        dom = self.input_handler.get_dom(cache_file_name=cache_file_name, url=url, force_download=force_download)
        # TODO: make include_depth an argument
        include_depth = 1
        metadata, content = self.table_parser.parse(
            dom,
            table_id=table_id,
            include_depth=None,
            column_to_attr=self.column_to_attr,
            name_attr=self.name_attr,
            **kwargs,
        )
        # Complete metadata
        metadata.url = url
        metadata.table_id = table_id
        metadata.include_depth = include_depth
        metadata.column_to_attr = self.column_to_attr
        metadata.name_attr = self.name_attr

        model = SpecModel(
            metadata=metadata,
            content=content,
            **kwargs,
        )

        model.exclude_titles()

        try:
            self.model_store.save(model, json_file_path)
        except Exception as e:
            # Log or handle the error as appropriate for your application
            print(f"Warning: Failed to cache model to {json_file_path}: {e}")
        return model
