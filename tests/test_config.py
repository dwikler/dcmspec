import os
import json
import pytest
from dcmspec.config import Config


@pytest.fixture(autouse=True)
def patch_dirs(monkeypatch, tmp_path):
    # Create unique temp folder for each test for config file and for default cache and config folders
    # NOTE: tmp_path is a pytest fixture that provides a unique temporary directory for each test.
    cache_dir = tmp_path / "cache"
    config_dir = tmp_path / "config"
    monkeypatch.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    monkeypatch.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    return tmp_path

def test_default_config_sets_cache_dir():
    """Test that the default cache_dir is set and the directory is created."""
    config = Config(app_name="dcmspec_test")
    assert "cache_dir" in config.params
    assert os.path.exists(config.get_param("cache_dir"))

def test_set_and_get_param():
    """Test setting and getting a config parameter."""
    config = Config(app_name="dcmspec_test")
    config.set_param("cache_dir", "./cache")
    assert config.get_param("cache_dir") == "./cache"

def test_loads_params_from_file(tmp_path):
    """Test loading parameters from a config file."""
    config_path = tmp_path / "config.json"
    params = {"params": {"cache_dir": "./cache"}}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(params, f)
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    assert config.get_param("cache_dir") == "./cache"

def test_handles_invalid_json(tmp_path, capsys):
    """Test that invalid JSON in the config file is handled gracefully and prints an error."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("{invalid json}")
    # Should not raise exception as code handles this case
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    assert "cache_dir" in config.params
    # Assert the error message was printed
    captured = capsys.readouterr()
    assert "Failed to load configuration file" in captured.out

def test_save_config():
    """
    Test that save_config writes the correct data and that config persists after reload.
    """
    # Create a config file in default config folder
    config = Config(app_name="dcmspec_test")
    config.set_param("cache_dir", "./cache")
    config.save_config()
    # Read the config file
    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "params" in data
    assert data["params"]["cache_dir"] == "./cache"
    assert "cache_dir" in data

    # Check persistence of config file
    config2 = Config(app_name="dcmspec_test", config_file=config.config_file)
    assert config2.get_param("cache_dir") == "./cache"

def _raise_oserror(*args, **kwargs):
    raise OSError("Simulated write failure")

def test_save_config_failure(monkeypatch, capsys):
    """Test that save_config prints an error message if saving fails."""
    config = Config(app_name="dcmspec_test")
    config.set_param("cache_dir", "./cache")

    # Simulate failure by making open() raise OSError
    monkeypatch.setattr("builtins.open", _raise_oserror)
    config.save_config()
    captured = capsys.readouterr()
    assert "Failed to save configuration file" in captured.out
    assert "Simulated write failure" in captured.out