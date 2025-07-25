# DCMSPEC Explorer

A GUI application for exploring DICOM specifications interactively.

## Running the Application

```bash
# From the project root
python -m src.dcmspec.apps.dcmspec_explorer

# Or with poetry
poetry run python -m src.dcmspec.apps.dcmspec_explorer
```

## Configuration

The application supports customizable configuration through JSON files. Configuration files are searched in the following order:

1. Current directory: `dcmspec_explorer_config.json`
2. User config: `~/.config/dcmspec/dcmspec_explorer_config.json`
3. App config directory: `src/dcmspec/apps/dcmspec_explorer/config/dcmspec_explorer_config.json`
4. Legacy location: Same directory as script

For detailed configuration options and examples, see the [config directory](config/README.md).

## Features

- Browse DICOM IODs (Information Object Definitions)
- Explore IOD modules and attributes hierarchically
- Sort and filter IOD lists
- Configurable logging levels
- Persistent caching of downloaded specifications
- Context menus for advanced options

## Configuration Examples

The `config/` directory contains several example configurations:

- **Default**: Basic configuration with INFO logging
- **Debug**: Verbose logging for troubleshooting
- **Minimal**: Minimal logging for production use

Copy any example to one of the search locations and rename to `dcmspec_explorer_config.json` to use it.
