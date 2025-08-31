"""Progress tracking classes for monitoring long-running operations in dcmspec."""

import types
import warnings
import inspect
from typing import Callable, Optional
from enum import Enum, auto

class Progress:
    """Represent the progress of a long-running operation.

    Args:
        percent (int): The progress percentage (0-100).
        status (ProgressStatus, optional): A machine-readable status code (see ProgressStatus enum).
            Clients are responsible for mapping this code to a user-facing string or UI element.
        step (int, optional): The current step number in a multi-step process (1-based).
        total_steps (int, optional): The total number of steps in the process.

    """

    def __init__(self, percent: int, status: 'ProgressStatus' = None, step: int = None, total_steps: int = None):
        """Initialize the progress private attributes.
        
        This class is immutable: the percent value is set at initialization and should not be changed.
        To report new progress, create a new Progress instance.

        Args:
            percent (int): The progress percentage (0-100).
            status (ProgressStatus, optional): A status code indicating the current operation.
            step (int, optional): The current step number in a multi-step process (1-based).
            total_steps (int, optional): The total number of steps in the process.
                    
        """
        self._percent = percent
        self._status = status
        self._step = step
        self._total_steps = total_steps

    @property
    def percent(self) -> int:
        """Get the progress percentage."""
        return self._percent

    @property
    def status(self) -> Optional['ProgressStatus']:
        """Get the progress status."""
        return self._status

    @property
    def step(self) -> Optional[int]:
        """Get the current step number."""
        return self._step

    @property
    def total_steps(self) -> Optional[int]:
        """Get the total number of steps."""
        return self._total_steps

    def __setattr__(self, name, value):
        """Prevent modification of attributes after initialization."""
        if hasattr(self, name):
            raise AttributeError(f"{self.__class__.__name__} is immutable. Cannot modify '{name}'.")
        super().__setattr__(name, value)
        
class ProgressStatus(Enum):
    """Enumeration of progress statuses.

    This enum defines the various states that a long-running operation can be in.

    | Name                    | Value | Description                                            |
    |-------------------------|--------|-------------------------------------------------------|
    | DOWNLOADING             | auto() | Generic download (e.g., a document)                   |
    | DOWNLOADING_IOD         | auto() | Downloading the IOD specification document (Part 3)   |
    | PARSING_TABLE           | auto() | Parsing a DICOM table                                 |
    | PARSING_IOD_MODULE_LIST | auto() | Parsing the list of modules in the IOD                |
    | PARSING_IOD_MODULES     | auto() | Parsing the IOD modules                               |
    | SAVING_MODEL            | auto() | Saving a specification model to disk                  |
    | SAVING_IOD_MODEL        | auto() | Saving the IOD model to disk                          

    Example:
        In your application, you can use ProgressStatus to present progress information to users:

        ```python
        from dcmspec.progress import ProgressStatus

        def progress_observer(progress):
            if progress.status == ProgressStatus.DOWNLOADING_IOD:
                print(f"Downloading IOD... {progress.percent}%")
        ```

    """

    DOWNLOADING = auto()  # Generic download (e.g., a document)
    DOWNLOADING_IOD = auto()  # Downloading the IOD specification document (Part 3)
    PARSING_TABLE = auto()  # Parsing a DICOM table
    PARSING_IOD_MODULE_LIST = auto()  # Parsing the list of modules in the IOD
    PARSING_IOD_MODULES = auto()  # Parsing the IOD modules
    SAVING_MODEL = auto()  # Saving a specification model to disk
    SAVING_IOD_MODEL = auto()  # Saving the IOD model to disk

def add_progress_step(
    step: int, total_steps: int, status: Optional[ProgressStatus] = None
) -> Callable[[Callable[[Progress], None]], Callable[[Progress], None]]:
    """Define a decorator to enrich progress events with step, total_steps, and optionally status."""
    def decorator(observer: Callable[[Progress], None]) -> Callable[[Progress], None]:
        def wrapper(progress: Progress) -> None:
            """Wrap the observer to include step, total_steps, and optionally status in the Progress object."""
            enriched = Progress(
                progress.percent,
                status=status if status is not None else progress.status,
                step=step,
                total_steps=total_steps
            )
            observer(enriched)
        return wrapper
    return decorator

def offset_progress_steps(
    step_offset: int, total_steps: int
) -> Callable[[Callable[[Progress], None]], Callable[[Progress], None]]:
    """Define a decorator to offset progress steps by a fixed amount."""
    def decorator(observer: Callable[[Progress], None]) -> Callable[[Progress], None]:
        def wrapper(progress: Progress) -> None:
            # Only update step/total_steps if they are set
            step = progress.step + step_offset if progress.step is not None else None
            observer(
                Progress(
                    progress.percent,
                    status=progress.status,
                    step=step,
                    total_steps=total_steps
                )
            )
        return wrapper
    return decorator

def calculate_percent(downloaded: int, total: int) -> int:
    """Calculate percent complete, rounded, or -1 if total is unknown/invalid."""
    if not total or total <= 0:
        return -1
    return min(round(downloaded * 100 / total), 100)

def handle_legacy_callback(
    progress_observer: Optional[Callable[[Progress], None]] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Optional[Callable[[Progress], None]]:
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

def adapt_progress_observer(observer: Optional[Callable]) -> Optional[Callable[[Progress], None]]:
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
    if isinstance(observer, types.FunctionType):
        sig = inspect.signature(observer)
        params = list(sig.parameters.values())
        if len(params) == 1:
            param = params[0]
            if param.annotation in (int, inspect._empty):
                warned = {"emitted": False}
                def wrapper(progress):
                    """Create a closure that adapts a legacy int progress callback to a Progress observer.

                    The original observer function is captured in this closure — a nested function that remembers
                    variables from the outer scope — so the returned wrapper will always call the correct callback.
                    This allows us to adapt a legacy int callback to a Progress observer without using a class.
                    """
                    if not warned["emitted"]:
                        warnings.warn(
                            "Passing a progress callback that accepts an int is deprecated. "
                            "Update your callback to accept a Progress object.",
                            DeprecationWarning,
                            stacklevel=2
                        )
                        warned["emitted"] = True
                    return observer(progress.percent)
                return wrapper
    return observer

class ProgressObserver:
    """Observer for monitoring progress updates."""

    def __call__(self, progress: Progress) -> None:
        """Handle progress updates.

        Args:
            progress (Progress): The current progress state.

        """
        # Override in client code or pass a function as observer
        pass