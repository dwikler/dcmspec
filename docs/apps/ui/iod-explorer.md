# IOD Explorer

A GUI application for exploring DICOM IOD specifications interactively.

## Dependencies

- **tkhtmlview** (required for the GUI, but now installed only if you request the GUI extra)
- **tkinter** (required for the GUI, but not installed via pip or Poetry)

> **Note:**  
> `tkinter` is part of the Python standard library, but on some Linux distributions and on macOS with Homebrew Python, it must be installed separately.
>
> - On **Ubuntu/Debian**: `sudo apt install python3-tk`
> - On **Fedora**: `sudo dnf install python3-tkinter`
> - On **macOS (Homebrew Python)**: `brew install tcl-tk`
>   - You may also need to set environment variables so Python can find the Tk libraries. See [Homebrew Python and Tkinter](https://docs.brew.sh/Homebrew-and-Python#tkinter) for details.
> - On **Windows/macOS (python.org installer)**: Usually included with the official Python installer.
>
> If you get an error about `tkinter` not being found, please install it as shown above.

## Installation

Clone the repository and install dependencies with Poetry:

```bash
git clone https://github.com/dwikler/dcmspec.git
cd dcmspec
poetry install --with gui
```

Or, with pip (from the repo root):

```bash
pip install .[gui]
```

This installs the package and its dependencies from your local source directory, including the GUI dependencies.  
If you want to make changes to the code and have them reflected immediately, use:

```bash
pip install -e .[gui]
```

> **Tip:**  
> It is recommended to use a virtual environment (venv) before running `pip install .[gui]` to avoid installing packages globally.  
> Poetry manages a venv automatically, but if you use pip directly, create one with:
>
> ```bash
> python -m venv .venv
> source .venv/bin/activate  # On Unix/macOS
> .\.venv\Scripts\Activate.ps1  # On Windows PowerShell
> ```

## Running the Application

### Option 1: Using poetry run (recommended)

```bash
poetry run iod-explorer
```

### Option 2: Activate environment then run directly

```bash
# On Windows PowerShell
.\.venv\Scripts\Activate.ps1
iod-explorer

# On Unix/macOS
source .venv/bin/activate
iod-explorer
```

### Option 3: Using the module path

```bash
poetry run python -m src.dcmspec.apps.ui.iod_explorer.iod_explorer
```

### Note on Poetry 2.0+ Environment Activation

If you're using Poetry 2.0+, the `poetry env activate` command only prints the activation command but doesn't actually activate the environment in your current shell. For direct command execution, use one of these approaches:

- **Manual activation (Windows):** `.\.venv\Scripts\Activate.ps1`
- **Install shell plugin:** `poetry self add poetry-plugin-shell` then use `poetry shell`
- **Always use `poetry run`:** No activation needed

## Configuration

The application supports customizable configuration through JSON files. Configuration files are searched in the following order:

1. Current directory: `iod_explorer_config.json`
2. User config: `~/.config/dcmspec/iod_explorer_config.json`
3. App config directory: `src/dcmspec/apps/ui/iod_explorer/config/iod_explorer_config.json`
4. Legacy location: Same directory as script

For detailed configuration options and examples, see the config directory in the application source.

## Features

- Browse DICOM IODs (Information Object Definitions)
- Explore IOD modules and attributes hierarchically
- Persistent caching of downloaded specifications

## Configuration Examples

The application includes several example configurations:

- **Default**: Basic configuration with INFO logging
- **Debug**: Verbose logging for troubleshooting
- **Minimal**: Minimal logging for production use

Copy any example to one of the search locations and rename to `iod_explorer_config.json` to use it.
