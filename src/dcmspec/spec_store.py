"""Abstract base class for DICOM specification model storage backends in dcmspec.

Defines the SpecStore interface for loading and saving DICOM specification models.
"""
from typing import Optional
import logging
from abc import ABC, abstractmethod

from dcmspec.spec_model import SpecModel

class SpecStore(ABC):
    """Abstract base class for DICOM specification model storage backends.

    Subclasses should implement methods for loading and saving models.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the model store with an optional logger.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.

        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load(self, path: str) -> SpecModel:
        """Load a model from the specified path.

        Args:
            path (str): The path to the file or resource to load from.

        Returns:
            SpecModel: The loaded model.
            
        """
        pass

    @abstractmethod
    def save(self, model: SpecModel, path: str) -> None:
        """Save a model to the specified path.

        Args:
            model (SpecModel): The model to save.
            path (str): The path to the file or resource to save to.

        """
        pass
