"""Merger for combining DICOM specification models in dcmspec.

This module provides the SpecMerger class, which provides a method to merge
DICOM specifications from multiple models.
"""
import logging
import os

from dcmspec.config import Config
from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.spec_factory import SpecStore
from dcmspec.spec_model import SpecModel

class SpecMerger:
    """Merges multiple DICOM specification models.

    The SpecMerger class provides methods to combine and enrich DICOM SpecModel objects,
    supporting both path-based and node-based merging strategies. This is useful for
    workflows where you need to sequentially merge two or more models, such as enriching
    PS3.3 module attributes models with definitions from the PS3.6 data elements dictionary,
    or combining a PS3.3 specification with a PS3.4 SOP class and then enriching with an 
    IHE profile specification.
    """

    def __init__(self, config: Config = None, model_store: SpecStore = None, logger: logging.Logger = None):
        """Initialize the SpecMerger.

        Sets up the logger for the merger. If no logger is provided, a default logger is created.
        If no model_store is provided, defaults to JSONSpecStore.

        Args:
            config (Optional[Config]): Configuration object. If None, a default Config is created.
            model_store (Optional[SpecStore]): Store for loading and saving models. Defaults to JSONSpecStore.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = config or Config()
        self.model_store = model_store or JSONSpecStore(logger=self.logger)

    def merge_node(
        self,
        model1: SpecModel,
        model2: SpecModel,
        match_by: str = "name",
        attribute_name: str = None,
        merge_attrs: list[str] = None,
        json_file_name: str = None,
        force_update: bool = False,
    ) -> SpecModel:
        """Merge two DICOM SpecModel objects using the node merge method, with optional caching.

        This is a convenience method that calls merge_many with two models.

        Args:
            model1 (SpecModel): The first model.
            model2 (SpecModel): The second model to merge with the first.
            match_by (str, optional): "name" to match by node name, "attribute" to match by a specific attribute.
            attribute_name (str, optional): The attribute name to use for matching.
            merge_attrs (list[str], optional): List of attribute names to merge from the other model's node.
            json_file_name (str, optional): If provided, cache/load the merged model to/from this file.
            force_update (bool, optional): If True, always perform the merge and overwrite the cache.

        Returns:
            SpecModel: The merged SpecModel instance.

        """
        return self.merge_many(
            [model1, model2],
            method = "matching_node",
            match_by=match_by,
            attribute_names=[attribute_name],
            merge_attrs_list=[merge_attrs],
            json_file_name=json_file_name,
            force_update=force_update,
        )

    def merge_path(
        self,
        model1: SpecModel,
        model2: SpecModel,
        match_by: str = "name",
        attribute_name: str = None,
        merge_attrs: list[str] = None,
        json_file_name: str = None,
        force_update: bool = False,
    ) -> SpecModel:
        """Merge two DICOM SpecModel objects using the path merge method, with optional caching.

        This is a convenience method that calls merge_many with two models.

        Args:
            model1 (SpecModel): The first model.
            model2 (SpecModel): The second model to merge with the first.
            match_by (str, optional): "name" to match by node name, "attribute" to match by a specific attribute.
            attribute_name (str, optional): The attribute name to use for matching.
            merge_attrs (list[str], optional): List of attribute names to merge from the other model's node.
            json_file_name (str, optional): If provided, cache/load the merged model to/from this file.
            force_update (bool, optional): If True, always perform the merge and overwrite the cache.

        Returns:
            SpecModel: The merged SpecModel instance.

        """
        return self.merge_many(
            [model1, model2],
            method = "matching_path",
            match_by=match_by,
            attribute_names=[attribute_name],
            merge_attrs_list=[merge_attrs],
            json_file_name=json_file_name,
            force_update=force_update,
        )

    def merge_many(
        self,
        models: list[SpecModel],
        method: str = "matching_path",
        match_by: str = "name",
        attribute_names: list = None,
        merge_attrs_list: list = None,
        json_file_name: str = None,
        force_update: bool = False,
    ) -> SpecModel:
        """Merge a sequence of DICOM SpecModel objects using the specified merge method, with optional caching.

        This method merges a list of models in order, applying either path-based or node-based
        merging at each step. You can specify different attribute names and lists of attributes
        to merge for each step, allowing for flexible, multi-stage enrichment of DICOM models.
        If json_file_name is provided, the merged model will be cached to that file, and loaded from
        cache if available and force_update is False.

        Args:
            models (list of SpecModel): The models to merge, in order.
            method (str): Merge method to use ("matching_path" or "matching_node").
            match_by (str, optional): "name" to match by node name, "attribute" to match by a specific attribute.
            attribute_names (list, optional): List of attribute names to use for each merge step.
                Each entry corresponds to a merge operation between two models.
            merge_attrs_list (list, optional): List of lists of attribute names to merge for each merge step.
                Each entry corresponds to a merge operation between two models.
            json_file_name (str, optional): If provided, cache/load the merged model to/from this file.
            force_update (bool, optional): If True, always perform the merge and overwrite the cache.

        Returns:
            SpecModel: The final merged SpecModel instance.

        Raises:
            ValueError: If models is empty, method is unknown, or attribute_names/merge_attrs_list
                have incorrect length.

        """
        orig_col2attr = None
        if models and hasattr(models[0].metadata, "column_to_attr"):
            orig_col2attr = models[0].metadata.column_to_attr
        cached_model = self._load_merged_model_from_cache(json_file_name, force_update, merge_attrs_list, orig_col2attr)
        if cached_model is not None:
            return cached_model

        self._validate_merge_args(models, attribute_names, merge_attrs_list)
        merged = self._merge_models(
            models, method=method, match_by=match_by, attribute_names=attribute_names, merge_attrs_list=merge_attrs_list
            )
        self._update_metadata(merged, models, merge_attrs_list)
        self._save_cache(merged, json_file_name)
        return merged

    def _validate_merge_args(
        self,
        models: list[SpecModel],
        attribute_names: list,
        merge_attrs_list: list,
    ) -> None:
        """Validate and normalize merge arguments for merging models."""
        if not models:
            raise ValueError("No models to merge")
        n_merges = len(models) - 1
        if attribute_names is None:
            attribute_names = [None] * n_merges
        elif not isinstance(attribute_names, list):
            attribute_names = [attribute_names] * n_merges
        if merge_attrs_list is None:
            merge_attrs_list = [None] * n_merges
        elif (
            not isinstance(merge_attrs_list, list)
            or (
                merge_attrs_list
                and not isinstance(merge_attrs_list[0], list)
            )
        ):
            merge_attrs_list = [merge_attrs_list] * n_merges
        if len(attribute_names) != n_merges:
            raise ValueError(
                f"Length of attribute_names ({len(attribute_names)}) "
                f"does not match number of merges ({n_merges})"
            )
        if len(merge_attrs_list) != n_merges:
            raise ValueError(
                f"Length of merge_attrs_list ({len(merge_attrs_list)}) "
                f"does not match number of merges ({n_merges})"
                )

    def _merge_models(
        self,
        models: list[SpecModel],
        method: str = "matching_path",
        match_by: str = "name",
        attribute_names: list = None,
        merge_attrs_list: list = None,
    ) -> SpecModel:
        """Perform the actual merging of models using the specified method."""
        merged = models[0]
        if method not in ("matching_path", "matching_node"):
            raise ValueError(f"Unknown merge method: {method}")

        for i, model in enumerate(models[1:]):
            attribute_name = attribute_names[i]
            merge_attrs = merge_attrs_list[i]
            if method == "matching_path":
                merged = merged.merge_matching_path(
                    model, match_by=match_by, attribute_name=attribute_name, merge_attrs=merge_attrs
                    )
            elif method == "matching_node":
                merged = merged.merge_matching_node(
                    model, match_by=match_by, attribute_name=attribute_name, merge_attrs=merge_attrs
                    )
        return merged

    def _update_metadata(
        self,
        merged: SpecModel,
        models: list[SpecModel],
        merge_attrs_list: list,
    ) -> None:
        """Update the metadata of the merged model to reflect merged attributes."""
        # Start with the original metadata
        meta = merged.metadata
        orig_header = list(getattr(meta, "header", []))
        orig_col2attr = dict(getattr(meta, "column_to_attr", {}))

        # Find the next available column index
        next_col = max(int(idx) for idx in orig_col2attr) + 1 if orig_col2attr else 0
        # For each merged-in model, add new merged attributes if not already present
        for i, model in enumerate(models[1:]):
            merge_attrs = merge_attrs_list[i]
            other_meta = getattr(model, "metadata", None)
            if other_meta is not None and merge_attrs:
                other_header = getattr(other_meta, "header", None)
                other_col2attr = getattr(other_meta, "column_to_attr", None)
                if other_header and other_col2attr:
                    for idx, attr in other_col2attr.items():
                        if attr in merge_attrs and attr not in orig_col2attr.values():
                            # Add new column for this attribute
                            if isinstance(other_header, list) and int(idx) < len(other_header):
                                orig_header.append(other_header[int(idx)])
                            else:
                                orig_header.append(attr)
                            orig_col2attr[next_col] = attr
                            next_col += 1

        if hasattr(meta, "header"):
            meta.header = orig_header
        if hasattr(meta, "column_to_attr"):
            meta.column_to_attr = orig_col2attr

    def _save_cache(
        self,
        merged: SpecModel,
        json_file_name: str,
    ) -> None:
        """Save the merged model to cache if a json_file_name is provided."""
        if json_file_name:
            merged_json_file_path = os.path.join(
                self.config.get_param("cache_dir"), "model", json_file_name
            )
            try:
                self.model_store.save(merged, merged_json_file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cache merged model to {merged_json_file_path}: {e}")
        else:
            self.logger.info("No json_file_name specified; merged model not cached.")

    def _load_merged_model_from_cache(
        self,
        json_file_name: str,
        force_update: bool,
        merge_attrs_list: list = None,
        orig_col2attr: dict = None,
    ) -> SpecModel | None:
        """Return the cached merged model if available, valid, and not force_update, else None."""
        merged_json_file_path = None
        if json_file_name:
            merged_json_file_path = os.path.join(
                self.config.get_param("cache_dir"), "model", json_file_name
            )
        if merged_json_file_path and os.path.exists(merged_json_file_path) and not force_update:
            try:
                model = self.model_store.load(merged_json_file_path)
                # Check that all requested merge attributes are present in the cached model's metadata
                if merge_attrs_list:
                    all_attrs = set()
                    for attrs in merge_attrs_list:
                        if attrs:
                            all_attrs.update(attrs)
                    col2attr = getattr(model.metadata, "column_to_attr", {})
                    orig_attrs = set(orig_col2attr.values()) if orig_col2attr else set()
                    # All requested attributes must be present
                    if any(attr not in col2attr.values() for attr in all_attrs):
                        self.logger.info(
                            f"Cached model at {merged_json_file_path} missing required merged attributes {all_attrs}; "
                            f"ignoring cache."
                        )
                        return None
                    # No extra attributes except those in the original model
                    allowed_attrs = all_attrs | orig_attrs
                    extra_attrs = set(col2attr.values()) - allowed_attrs
                    if extra_attrs:
                        self.logger.info(
                            f"Cached model at {merged_json_file_path} contains extra attributes {extra_attrs} "
                            f"not requested; ignoring cache."
                        )
                        return None
                self.logger.info(
                    f"Loaded model from cache {merged_json_file_path}"
                )
                return model
            except Exception as e:
                self.logger.warning(
                    f"Failed to load merged model from cache {merged_json_file_path}: {e}"
                )
        return None