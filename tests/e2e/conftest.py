"""Shared fixtures for the e2e canary suite."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def e2e_cache_dirs(tmp_path_factory):
    """Patch platformdirs' cache/config dirs once for the whole e2e session.

    Normally Config resolves the cache dir via platformdirs.user_cache_dir("dcmspec") to a
    permanent, OS-specific location (e.g. ~/Library/Caches/dcmspec on macOS) that persists across
    runs. Here that's redirected to a directory under pytest's own tmp_path_factory tree instead,
    so the e2e suite never touches or depends on that real, permanent cache: each run starts from
    a clean slate. pytest manages that tmp_path_factory directory's lifecycle itself (retention
    policy, cleanup of older runs) — see tmp_path_retention_count/tmp_path_retention_policy.

    Scoped to the session (not per-test, unlike tests/unit/conftest.py's `patch_dirs`) so the
    real Part 3 and Part 6 documents are each downloaded once and shared across the tests in
    this suite, instead of once per test.
    """
    base = tmp_path_factory.mktemp("e2e")
    cache_dir = base / "cache"
    config_dir = base / "config"
    print(f"\ne2e cache dir: {cache_dir}")  # visible with pytest -s
    mp = pytest.MonkeyPatch()
    mp.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    mp.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    yield base
    mp.undo()


@pytest.fixture(scope="session")
def e2e_output_dir(e2e_cache_dirs):
    """Directory for tests to write their full printed output to, instead of flooding stdout.

    Alongside e2e_cache_dirs' cache/config dirs, so it's easy to find: a full tree of a large
    model (e.g. the IOD test's ~27 modules) can run to thousands of lines, impractical to print
    directly even with pytest -s. Tests write there via SpecPrinter(model, output=path) and print
    just the file path, keeping -s output short while the full detail stays available on disk.
    """
    output_dir = e2e_cache_dirs / "output"
    output_dir.mkdir()
    return output_dir
