"""Section image resolver class for downloading and caching a section's referenced images in dcmspec."""
import logging
import os
from typing import List, Optional
from urllib.parse import urljoin

from dcmspec.doc_handler import DocHandler
from dcmspec.spec_model import SpecModel


class SectionImageResolver:
    """Downloads and caches the images a parsed section references.

    Used with a model built by DOMSectionSpecParser, whose metadata.image_srcs lists the
    section's images as raw, unresolved paths.
    """

    def __init__(self, doc_handler: DocHandler, cache_dir: str, logger: Optional[logging.Logger] = None):
        """Initialize the SectionImageResolver.

        Args:
            doc_handler (DocHandler): Handler used to download each image.
            cache_dir (str): Root cache directory; images are cached under
                "<cache_dir>/standard/figures/".
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default
                logger is created.

        """
        self.doc_handler = doc_handler
        self.cache_dir = cache_dir
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def resolve(self, section_model: SpecModel, url: str, force_download: bool = False) -> None:
        """Download a section's images, recording local paths.

        Populates `section_model.metadata.image_paths`, parallel to `metadata.image_srcs`
        (Relative path to cache_dir/standard/ or None for an image that failed to download).

        Args:
            section_model (SpecModel): A model built by DOMSectionSpecParser.
            url (str): The URL the section's document was loaded from, used to resolve
                image_srcs into absolute URLs.
            force_download (bool): If True, re-download and overwrite even an already-cached
                image.

        """
        image_paths: List[Optional[str]] = []
        for image_src in section_model.metadata.image_srcs:
            image_path = os.path.join("figures", os.path.basename(image_src))
            file_path = os.path.join(self.cache_dir, "standard", image_path)
            try:
                self.doc_handler.download_if_needed(
                    urljoin(url, image_src), file_path, force=force_download, binary=True
                )
                image_paths.append(image_path)
            except RuntimeError as e:
                self.logger.warning(f"Failed to download image '{image_src}': {e}")
                image_paths.append(None)
        section_model.metadata.image_paths = image_paths
