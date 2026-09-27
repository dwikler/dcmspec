"""Tests for the SpecStore abstract base class in dcmspec.spec_store."""
import pytest
from dcmspec.spec_store import SpecStore


def test_cannot_instantiate_without_file_extension():
    """Test that a SpecStore subclass missing file_extension cannot be instantiated."""
    class IncompleteStore(SpecStore):
        def load(self, path):
            pass

        def save(self, model, path):
            pass

    with pytest.raises(TypeError):
        IncompleteStore()
