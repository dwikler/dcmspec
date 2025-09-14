# IOD Explorer Configuration

This directory contains configuration files and documentation for the IOD Explorer GUI application.

## Table of Contents

- [Configuration File Search Order](#configuration-file-search-order)
- [Configuration Options](#configuration-options)
- [Example Configuration Files](#example-configuration-files)
- [Configuration Files in This Directory](#configuration-files-in-this-directory)
- [Quick Configuration Test](#quick-configuration-test)
- [Testing Configuration Priority](#testing-configuration-priority)

## Configuration File Search Order

The application searches for configuration files in the following priority order:

### Tier 1: App-Specific Configuration Files

1. `iod_explorer_config.json` in the current directory
2. `~/.config/dcmspec/iod_explorer_config.json` in the user config directory
3. `iod_explorer_config.json` in this app config directory (`src/dcmspec/apps/iod_explorer/config/`)
4. `iod_explorer_config.json` in the same directory as the script (legacy support)

### Tier 2: Base Library Configuration (Fallback)

If no app-specific config is found, the base `Config` class looks for:

- **macOS**: `~/Library/Application Support/iod_explorer/config.json`
- **Linux**: `~/.config/iod_explorer/config.json`
- **Windows**: `%USERPROFILE%\AppData\Local\iod_explorer\config.json`

### Default Behavior (No Config Files)

If no configuration files are found anywhere, the application uses:

- **Cache directory**: Platform-specific cache directory (e.g., `~/Library/Caches/iod_explorer`)
- **Log level**: INFO

## Configuration Options

### `cache_dir`

- **Type**: String
- **Default**: Platform-specific cache directory (e.g., `~/Library/Caches/iod_explorer` on macOS)
- **Description**: Directory to store downloaded DICOM specifications and cached models

### `log_level`

- **Type**: String
- **Default**: "INFO"
- **Valid values**: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- **Description**: Sets the logging level for the application

## Example Configuration Files

### Default Configuration

```json
{
  "cache_dir": "./cache",
  "log_level": "INFO"
}
```

### Debug Configuration (Verbose Logging)

```json
{
  "cache_dir": "/tmp/debug_cache",
  "log_level": "DEBUG"
}
```

### Minimal Logging Configuration

```json
{
  "cache_dir": "~/Documents/iod_explorer_cache",
  "log_level": "WARNING"
}
```

## Configuration Files in This Directory

This directory contains several example configuration files which you can use as templates for your own configuration:

- **`iod_explorer_config.json`**: Default configuration with INFO logging
- **`iod_explorer_config_example.json`**: Basic example configuration
- **`iod_explorer_config_debug.json`**: Debug configuration with verbose logging
- **`iod_explorer_config_minimal_logging.json`**: Minimal logging configuration

To use a template:

1. Copy the desired config file to one of the search locations (see above)
2. Rename it to `iod_explorer_config.json`
3. Modify settings as needed
4. Start the IOD Explorer application

The application will automatically detect and use the configuration file. You'll see log messages indicating which configuration file was loaded and the current settings.

## Quick Configuration Test

You can test your configuration without running the full GUI:

> **Note:**
> Before running the command below, make sure you are in the root of your dcmspec project directory (`cd /path/to/dcmspec`).
> Also, if you are not using the default `.venv` virtual environment, replace `.venv/bin/python` with the path to your Python executable.

```bash
.venv/bin/python -c "\
from dcmspec.apps.ui.iod_explorer.iod_explorer import load_app_config, setup_logger; \
config = load_app_config(); \
logger = setup_logger(config); \
print(); \
print(f'Config file: {config.config_file}'); \
print(f'Cache dir: {config.cache_dir}'); \
print(f'Log level: {config.get_param(\"log_level\")}'); \
logger.info('Test log message'); \
logger.debug('Debug message')"
```

## Testing Configuration Priority

To test the configuration search order, run the following command to create a test config file and see which config file is detected and used:

> **Note:**
> Before running the command below, make sure you are in the root of your dcmspec project directory (`cd /path/to/dcmspec`).
> Also, if you are not using the default `.venv` virtual environment, replace `.venv/bin/python` with the path to your Python executable.

The command below will create a file named iod_explorer_config.json in your current directory.  
You may want to delete this file after testing to avoid it taking precedence over other config files in future runs.

```bash
echo '{"cache_dir": "./app_cache", "log_level": "INFO"}' > iod_explorer_config.json

.venv/bin/python -c "\
from dcmspec.apps.ui.iod_explorer.iod_explorer import load_app_config, setup_logger; \
config = load_app_config(); \
logger = setup_logger(config); \
print(); \
logger.info('Starting IOD Explorer'); \
log_level = config.get_param('log_level') or 'INFO'; \
source = 'app-specific' if 'iod_explorer_config.json' in (config.config_file or '') else 'default'; \
logger.info(f'Logging configured: level={log_level.upper()}, source={source}'); \
logger.info(f'Config file: {config.config_file or \"none (using defaults)\"}'); \
logger.info(f'Cache directory: {config.cache_dir}');"
```

You should see output similar to the following:

```text
INFO - Starting IOD Explorer
INFO - Logging configured: level=INFO, source=app-specific
INFO - Config file: iod_explorer_config.json
INFO - Cache directory: ./app_cache
```

To clean up after testing, you can remove the file:

```bash
rm iod_explorer_config.json
```

The application will display important configuration information at startup, including:

- **Log level and source**: Whether config comes from app-specific file or defaults
- **Config file location**: Exact path to the configuration file being used
- **Cache directory**: Where downloaded specifications and models are stored

This information helps with troubleshooting and understanding the application's configuration.
