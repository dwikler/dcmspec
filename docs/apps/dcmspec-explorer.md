# DCMSPEC Explorer

A GUI application for exploring DICOM specifications interactively.

## Running the Application

### Option 1: Using poetry run (recommended)
```bash
poetry run dcmspec-explorer
```

### Option 2: Activate environment then run directly
```bash
# On Windows PowerShell
.\.venv\Scripts\Activate.ps1
dcmspec-explorer

# On Unix/macOS
source .venv/bin/activate
dcmspec-explorer
```

### Option 3: Using the module path
```bash
poetry run python -m src.dcmspec.apps.dcmspec_explorer.dcmspec_explorer
```

### Note on Poetry 2.0+ Environment Activation

If you're using Poetry 2.0+, the `poetry env activate` command only prints the activation command but doesn't actually activate the environment in your current shell. For direct command execution, use one of these approaches:

- **Manual activation (Windows):** `.\.venv\Scripts\Activate.ps1`
- **Install shell plugin:** `poetry self add poetry-plugin-shell` then use `poetry shell`
- **Always use `poetry run`:** No activation needed

## Configuration

The application supports customizable configuration through JSON files. Configuration files are searched in the following order:

1. Current directory: `dcmspec_explorer_config.json`
2. User config: `~/.config/dcmspec/dcmspec_explorer_config.json`
3. App config directory: `src/dcmspec/apps/dcmspec_explorer/config/dcmspec_explorer_config.json`
4. Legacy location: Same directory as script

For detailed configuration options and examples, see the config directory in the application source.

## Features

- Browse DICOM IODs (Information Object Definitions)
- Explore IOD modules and attributes hierarchically
- Sort and filter IOD lists
- Configurable logging levels
- Persistent caching of downloaded specifications
- Context menus for advanced options

## Configuration Examples

The application includes several example configurations:

- **Default**: Basic configuration with INFO logging
- **Debug**: Verbose logging for troubleshooting
- **Minimal**: Minimal logging for production use

Copy any example to one of the search locations and rename to `dcmspec_explorer_config.json` to use it.
