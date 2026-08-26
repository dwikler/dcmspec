"""Shared fixtures for the e2e canary suite."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def e2e_cache_dirs(tmp_path_factory):
    """Patch platformdirs' cache/config dirs once for the whole e2e session.

    Scoped to the session (not per-test, unlike tests/unit/conftest.py's `patch_dirs`) so the
    real Part 3 and Part 6 documents are each downloaded once and shared across the tests in
    this suite, instead of once per test.
    """
    cache_dir = tmp_path_factory.mktemp("e2e") / "cache"
    config_dir = tmp_path_factory.mktemp("e2e") / "config"
    mp = pytest.MonkeyPatch()
    mp.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    mp.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    yield
    mp.undo()
