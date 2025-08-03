"""DCMSPEC Explorer application package.

This package contains the DCMSPEC Explorer GUI application for browsing
DICOM specifications interactively.
"""

from .dcmspec_explorer import main, DCMSpecExplorer

__all__ = ['main', 'DCMSpecExplorer']
