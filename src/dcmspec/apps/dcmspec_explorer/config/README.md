# DCMSPEC Explorer Configuration

This directory contains configuration files and documentation for the DCMSPEC Explorer GUI application.

## Configuration File Search Order

The application searches for configuration files in the following priority order:

### Tier 1: App-Specific Configuration Files

1. `dcmspec_explorer_config.json` in the current directory
2. `~/.config/dcmspec/dcmspec_explorer_config.json` in the user config directory
3. `dcmspec_explorer_config.json` in this app config directory (`src/dcmspec/apps/dcmspec_explorer/config/`)
4. `dcmspec_explorer_config.json` in the same directory as the script (legacy support)

### Tier 2: Base Library Configuration (Fallback)

If no app-specific config is found, the base `Config` class looks for:

- **macOS**: `~/Library/Application Support/dcmspec_explorer/config.json`
- **Linux**: `~/.config/dcmspec_explorer/config.json`
- **Windows**: `%USERPROFILE%\AppData\Local\dcmspec_explorer\config.json`

### Default Behavior (No Config Files)

If no configuration files are found anywhere, the application uses:

- **Cache directory**: Platform-specific cache directory (e.g., `~/Library/Caches/dcmspec_explorer`)
- **Log level**: INFO

## Configuration Options

### `cache_dir`

- **Type**: String
- **Default**: Platform-specific cache directory (e.g., `~/Library/Caches/dcmspec_explorer` on macOS)
- **Description**: Directory to store downloaded DICOM specifications and cached models

### `log_level`

- **Type**: String
- **Default**: "INFO"
- **Valid values**: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- **Description**: Sets the logging level for the application

## Configuration Files in This Directory

This directory contains several example configuration files:

- **`dcmspec_explorer_config.json`**: Default configuration with INFO logging
- **`dcmspec_explorer_config_example.json`**: Basic example configuration
- **`dcmspec_explorer_config_debug.json`**: Debug configuration with verbose logging
- **`dcmspec_explorer_config_minimal_logging.json`**: Minimal logging configuration

To use any of these configurations:

1. Copy the desired config file to one of the search locations (see above)
2. Rename it to `dcmspec_explorer_config.json`
3. Modify settings as needed

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
  "cache_dir": "/tmp/dcmspec_debug_cache",
  "log_level": "DEBUG"
}
```

### Minimal Logging Configuration

```json
{
  "cache_dir": "~/Documents/dcmspec_cache",
  "log_level": "WARNING"
}
```

## Testing Configuration Priority

You can test the configuration search order and see the logging output:

```bash
cd /path/to/dcmspec

# Test with app-specific config (Tier 1)
echo '{"cache_dir": "./app_cache", "log_level": "INFO"}' > dcmspec_explorer_config.json
/path/to/python -c "
from src.dcmspec.apps.dcmspec_explorer import load_app_config, setup_logger
config = load_app_config()
logger = setup_logger(config)
logger.info('Starting DCMSPEC Explorer')
log_level = config.get_param('log_level') or 'INFO'
source = 'app-specific' if 'dcmspec_explorer_config.json' in (config.config_file or '') else 'default'
logger.info(f'Logging configured: level={log_level.upper()}, source={source}')
logger.info(f'Config file: {config.config_file or \"none (using defaults)\"}')
logger.info(f'Cache directory: {config.cache_dir}')
"

# Expected output:
# INFO - Starting DCMSPEC Explorer
# INFO - Logging configured: level=INFO, source=app-specific
# INFO - Config file: dcmspec_explorer_config.json
# INFO - Cache directory: ./app_cache
```

The application will display important configuration information at startup, including:

- **Log level and source**: Whether config comes from app-specific file or defaults
- **Config file location**: Exact path to the configuration file being used
- **Cache directory**: Where downloaded specifications and models are stored

This information helps with troubleshooting and understanding the application's configuration.

## Usage

You can test your configuration without running the full GUI:

```bash
cd /path/to/dcmspec
/path/to/python -c "
from src.dcmspec.apps.dcmspec_explorer import load_app_config, setup_logger
config = load_app_config()
logger = setup_logger(config)
print(f'Config file: {config.config_file}')
print(f'Cache dir: {config.cache_dir}')
print(f'Log level: {config.get_param(\"log_level\")}')
logger.info('Test log message')
logger.debug('Debug message')
"
```

## Usage

1. Copy one of the example configuration files to one of the supported locations
2. Rename it to `dcmspec_explorer_config.json`
3. Modify the settings as needed
4. Start the DCMSPEC Explorer application

The application will automatically detect and use the configuration file. You'll see log messages indicating which configuration file was loaded and the current settings.
