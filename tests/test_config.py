"""Tests for the Config class in dcmspec.config."""
import os
import json
import pytest
from dcmspec.config import Config


@pytest.fixture(autouse=True)
def patch_dirs(monkeypatch, tmp_path):
    """Patch platformdirs' user_cache_dir and user_config_dir to use unique temporary directories for each test."""
    cache_dir = tmp_path / "cache"
    config_dir = tmp_path / "config"
    monkeypatch.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(cache_dir))
    monkeypatch.setattr("dcmspec.config.user_config_dir", lambda app_name: str(config_dir))
    return tmp_path

def test_default_config_sets_cache_dir():
    """Test that the default cache_dir is set and the directory is created."""
    config = Config(app_name="dcmspec_test")
    assert "cache_dir" in config._data
    # Assert the property match the value in the config
    assert config.cache_dir == config.get_param("cache_dir")
    assert os.path.exists(config.get_param("cache_dir"))

def test_set_and_get_param():
    """Test setting and getting a config parameter."""
    config = Config(app_name="dcmspec_test")
    config.set_param("cache_dir", "./cache")
    assert config.get_param("cache_dir") == "./cache"

def test_loads_params_from_file(tmp_path):
    """Test loading parameters from a config file."""
    config_path = tmp_path / "config.json"
    params = {"cache_dir": "./cache"}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(params, f)
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    assert config.get_param("cache_dir") == "./cache"
    assert config.cache_dir == "./cache"

def test_handles_invalid_json(tmp_path, capsys):
    """Test that invalid JSON in the config file is handled gracefully and prints an error."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("{invalid json}")
    # Should not raise exception as code handles this case
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    assert "cache_dir" in config._data
    # Assert the error message was printed
    captured = capsys.readouterr()
    assert "Failed to load configuration file" in captured.out

def test_save_config():
    """Test save_config function in no config file case."""
    # Create a config file in default config folder
    config = Config(app_name="dcmspec_test")
    config.set_param("cache_dir", "./cache")
    config.save_config()
    # Read the config file
    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["cache_dir"] == "./cache"
    assert "cache_dir" in data

def test_save_config_updates_cache_dir(tmp_path):
    """Test save_config function in previous config file exists case."""
    config_path = tmp_path / "test_config.json"
    # Write a config with an initial cache_dir value
    config_data = {
        "cache_dir": "/tmp/old_cache"
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    # Confirm initial state
    assert config.get_param("cache_dir") == "/tmp/old_cache"
    # Update cache_dir and save
    config.set_param("cache_dir", "/tmp/new_cache")
    config.save_config()
    with open(config_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["cache_dir"] == "/tmp/new_cache"

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

def test_config_file_is_directory(tmp_path, capsys):
    """Test that if config_file is a directory, a warning is printed and default config is used."""
    config_dir = tmp_path / "myconfigdir"
    config_dir.mkdir()
    config = Config(app_name="dcmspec_test", config_file=str(config_dir))
    captured = capsys.readouterr()
    assert f"Warning: The config_file path '{config_dir}' is a directory, not a file." in captured.out
    # Should fall back to default config (cache_dir should be set to platformdirs default, not None)
    assert config.get_param("cache_dir") is not None

def test_cache_dir_fileexisterror(tmp_path, capsys):
    """Test that if cache_dir is set to a file, FileExistsError is handled."""
    cache_file = tmp_path / "not_a_dir"
    cache_file.write_text("this is a file, not a directory")
    config_path = tmp_path / "config.json"
    config_data = {"cache_dir": str(cache_file)}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    captured = capsys.readouterr()
    assert f"Error: The cache_dir path '{cache_file}' exists and is not a directory." in captured.out
    assert config.get_param("cache_dir") == str(cache_file)
    assert not os.path.isdir(cache_file)

def test_cache_dir_not_a_directory(tmp_path, capsys, monkeypatch):
    """Test handling of rare case where cache_dir is set to a path that is not a directory and makedirs did not fail."""
    cache_file = tmp_path / "not_a_dir"
    cache_file.write_text("This is a file, not a directory")
    config_path = tmp_path / "config.json"
    config_data = {"cache_dir": str(cache_file)}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    # Patch os.makedirs to do nothing.
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    config = Config(app_name="dcmspec_test", config_file=str(config_path))
    captured = capsys.readouterr()
    assert f"Error: The cache_dir path '{cache_file}' is not a directory." in captured.out
    assert config.get_param("cache_dir") == str(cache_file)
    assert not os.path.isdir(cache_file)
