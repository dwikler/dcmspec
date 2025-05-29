import os
import json
from platformdirs import user_cache_dir, user_config_dir


class Config:
    def __init__(self, app_name: str = "dcmspec", config_file: str = None):
        self.app_name = app_name
        self.config_file = config_file or os.path.join(user_config_dir(app_name), "config.json")

        # Initialize params with default values
        self.params = {"cache_dir": user_cache_dir(app_name)}

        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.params.update(config.get("params", {}))

        except (OSError, json.JSONDecodeError) as e:
            print(f"Failed to load configuration file {self.config_file}: {e}")

        # Create cache directory if it does not exist
        os.makedirs(self.get_param("cache_dir"), exist_ok=True)

    def save_config(self):
        # Save the current cache_dir (from params) and all params
        config = {
            "cache_dir": self.get_param("cache_dir"),
            "params": self.params
        }
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except OSError as e:
            print(f"Failed to save configuration file {self.config_file}: {e}")

    def set_param(self, key, value):
        self.params[key] = value

    def get_param(self, key):
        return self.params.get(key)
