import os
from typing import Optional, Dict

from dcmspec.config import Config
from dcmspec.spec_model import SpecModel
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.dom_table_spec_parser import DOMTableSpecParser


class SpecFactory:
    def __init__(
        self,
        input_handler: Optional[XHTMLDocHandler] = None,
        model_store: Optional[JSONSpecStore] = None,
        table_parser: Optional[DOMTableSpecParser] = None,
        column_to_attr: Dict[int, str] = None,
        name_attr: str = None,
        config: Optional[Config] = None,
    ):
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
        """
        Downloads (if needed) and parses an input file from a URL, builds the DICOMAttributeModel,
        and caches the result as JSON.

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

        json_file_name = json_file_name or (os.path.splitext(cache_file_name)[0] + ".json")
        json_file_path = os.path.join(self.config.get_param("cache_dir"), "model", json_file_name)
        if os.path.exists(json_file_path) and not force_download:
            try:
                metadata, content = self.model_store.load(json_file_path)
                print(f"Loaded model from cache {json_file_path}")
                model = SpecModel(
                    metadata=metadata,
                    content=content,
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

        # TODO: add exclude_titles argument with default to True
        model.exclude_module_titles()
        # TODO: add filter_required argument with default to False
        # model.filter_required("elem_type")
        # Always cache after building
        try:
            self.model_store.save(model, json_file_path)
        except Exception as e:
            # Log or handle the error as appropriate for your application
            print(f"Warning: Failed to cache model to {json_file_path}: {e}")
        return model
