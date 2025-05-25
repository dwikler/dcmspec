from typing import Any, Optional
import logging
from abc import ABC, abstractmethod


class SpecStore(ABC):
    """
    Abstract base class for DICOM attribute model storage backends.
    Subclasses should implement methods for loading and saving models.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the model store with an optional logger.

        Args:
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load(self, path: str) -> Any:
        """
        Loads a model from the specified path.

        Args:
            path (str): The path to the file or resource to load from.

        Returns:
            Any: The loaded model.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    @abstractmethod
    def save(self, model: Any, path: str) -> None:
        """
        Saves a model to the specified path.

        Args:
            model (Any): The model to save.
            path (str): The path to the file or resource to save to.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass
