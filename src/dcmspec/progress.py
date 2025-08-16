"""Progress tracking classes for monitoring long-running operations in dcmspec."""
import types
import warnings
from typing import Callable, Optional
from enum import Enum, auto

class ProgressStatus(Enum):
    """Enumeration of progress statuses."""

    DOWNLOADING = auto()  # Generic download (e.g., a document)
    DOWNLOADING_IOD = auto()  # Downloading the IOD specification document (Part 3)
    PARSING_TABLE = auto()  # Parsing a DICOM table
    PARSING_IOD_MODULE_LIST = auto()  # Parsing the list of modules in the IOD
    PARSING_IOD_MODULES = auto()  # Parsing the IOD modules
    SAVING_MODEL = auto()  # Saving a specification model to disk
    SAVING_IOD_MODEL = auto()  # Saving the IOD model to disk


def handle_legacy_callback(
    progress_observer: Optional[Callable] = None,
    progress_callback: Optional[Callable] = None,
) -> Optional[Callable]:
    """Resolve and return a progress_observer, handling legacy progress_callback and warning if both are provided.

    If both are provided, only progress_observer is used and a warning is issued.
    If only progress_callback is provided, it is adapted to a progress_observer.
    """
    if progress_observer is not None and progress_callback is not None:
        warnings.warn(
            "Both progress_observer and progress_callback were provided. "
            "This is not supported: only progress_observer will be used and progress_callback will be ignored. "
            "Do not pass both. progress_callback is deprecated and will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2
        )
    if progress_observer is None and progress_callback is not None:
        from dcmspec.progress import adapt_progress_observer
        return adapt_progress_observer(progress_callback)
    return progress_observer

def adapt_progress_observer(observer):
    """Wrap a progress observer or callback so it can accept either a Progress object or an int percent.

    This function provides backward compatibility for legacy progress callbacks that expect
    an integer percent value. If the observer is a plain function that takes a single argument
    (typed as `int` or untyped), it will be wrapped so that it receives `progress.percent`
    instead of the Progress object. A DeprecationWarning is issued when this legacy usage occurs.

    Only plain functions are wrapped; class instances or callables are left unchanged to avoid
    interfering with class-based observers that expect a Progress object.

    Args:
        observer (callable or None): The progress observer or callback.

    Returns:
        callable or None: An observer that always accepts a Progress object, or a wrapper that calls the
        original callback with progress.percent if it expects an int.

    Example:
        # Legacy callback (int)
        def my_callback(percent):
            print(f"Progress: {percent}%")

        # New-style callback (Progress)
        def my_observer(progress):
            print(f"Progress: {progress.percent}%")
        
    """
    if observer is None:
        return None
    import inspect
    if isinstance(observer, types.FunctionType):
        sig = inspect.signature(observer)
        params = list(sig.parameters.values())
        if len(params) == 1:
            param = params[0]
            if param.annotation in (int, inspect._empty):
                def wrapper(progress):
                    warnings.warn(
                        "Passing a progress callback that accepts an int is deprecated. "
                        "Update your callback to accept a Progress object.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                    return observer(progress.percent)
                return wrapper
    return observer

class Progress:
    """Represent the progress of a long-running operation.

    Args:
        percent (int): The progress percentage (0-100).
        status (ProgressStatus, optional): A machine-readable status code (see ProgressStatus enum).
            Clients are responsible for mapping this code to a user-facing string or UI element.

    """

    def __init__(self, percent: int, status: 'ProgressStatus' = None, step: int = None, total_steps: int = None):
        """Initialize the progress.

        This class is immutable: the percent value is set at initialization and should not be changed.
        To report new progress, create a new Progress instance.

        Args:
            percent (int): The progress percentage (0-100).
            status (ProgressStatus, optional): A status code indicating the current operation.
            step (int, optional): The current step number in a multi-step process (1-based).
            total_steps (int, optional): The total number of steps in the process.


        """
        self.percent = percent
        self.status = status
        self.step = step
        self.total_steps = total_steps

class ProgressObserver:
    """Observer for monitoring progress updates."""

    def __call__(self, progress: Progress):
        """Handle progress updates.

        Args:
            progress (Progress): The current progress state.

        """
        # Override in client code or pass a function as observer
        pass