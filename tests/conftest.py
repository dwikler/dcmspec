"""Shared pytest fixtures for the dcmspec test suite."""

import pytest

@pytest.fixture(autouse=True)
def patch_dirs(monkeypatch, tmp_path):
    """Patch platformdirs' user_cache_dir and user_config_dir to use unique temporary directories for each test."""
    cache_dir = tmp_path / "cache"
    config_dir = tmp_path / "config"
    monkeypatch.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    monkeypatch.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    print(f"Test temp directory {tmp_path}")
    return tmp_path
