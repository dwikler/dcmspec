"""Configuration management for the dcmspec library.

This module provides the Config class for managing application configuration,
including cache directory handling and user-defined parameters.
"""

import os
import json
from typing import Any, Optional, Dict
from platformdirs import user_cache_dir, user_config_dir


class Config:
    """Manages application configuration.

    Reserved configuration keys:
    - cache_dir: Cache Directory path used by the library. If not set by the user, OS-specific default is used.

    Users may add their own keys, but should not overwrite reserved keys unless they intend to change library behavior.
    """

    def __init__(self, app_name: str = "dcmspec", config_file: Optional[str] = None):
        """Initialize the Config object.

        Args:
            app_name: The application name used for determining default config/cache directories.
            config_file: Optional path to a specific config file. If not provided, a default location is used.

        """
        self.app_name: str = app_name
        self.config_file: str = config_file or os.path.join(user_config_dir(app_name), "config.json")

        # Check if config_file is a directory; if so, warn and fall back to default config
        if os.path.isdir(self.config_file):
            print(f"Warning: The config_file path '{self.config_file}' is a directory, not a file. Using default.")
            self._data: Dict[str, Any] = {"cache_dir": user_cache_dir(app_name)}
            return

        # Initialize config with OS-specific default value for cache directory
        self._data: Dict[str, Any] = {"cache_dir": user_cache_dir(app_name)}

        self.load_config()

    def load_config(self) -> None:
        """Load configuration from the config file if it exists.

        Creates the cache directory if it does not exist.
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config: Dict[str, Any] = json.load(f)
                    self._data.update(config)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Failed to load configuration file {self.config_file}: {e}")

        cache_dir = self.get_param("cache_dir")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except FileExistsError:
            print(f"Error: The cache_dir path '{cache_dir}' exists and is not a directory.")
            return

        # Handle rare case where the path may not be a directory and, for any reason, os.makedirs did not fail.
        if not os.path.isdir(cache_dir):
            print(f"Error: The cache_dir path '{cache_dir}' is not a directory.")
            return

    def save_config(self) -> None:
        """Save the current configuration to the config file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except OSError as e:
            print(f"Failed to save configuration file {self.config_file}: {e}")

    def set_param(self, key: str, value: Any) -> None:
        """Set a configuration parameter."""
        self._data[key] = value

    def get_param(self, key: str) -> Optional[Any]:
        """Get a configuration parameter by key."""
        return self._data.get(key)

    @property
    def cache_dir(self) -> str:
        """Access the cache directory used by the library."""
        return self.get_param("cache_dir")

