"""Progress tracking classes for monitoring long-running operations in dcmspec."""

import types
import warnings

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
                    import warnings
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
    """Represent the progress of a long-running operation."""

    def __init__(self, percent: int):
        """Initialize the progress.

        This class is immutable: the percent value is set at initialization and should not be changed.
        To report new progress, create a new Progress instance.

        Args:
            percent (int): The progress percentage (0-100).
        
        """
        self.percent = percent

class ProgressObserver:
    """Observer for monitoring progress updates."""

    def __call__(self, progress: Progress):
        """Handle progress updates.

        Args:
            progress (Progress): The current progress state.

        """
        # Override in client code or pass a function as observer
        pass