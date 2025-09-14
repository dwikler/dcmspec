# IOD Explorer

A GUI application for exploring DICOM specifications interactively.

## Documentation

For complete documentation including installation, configuration, and usage instructions, see:

**[IOD Explorer Documentation](../../../../../docs/apps/iod-explorer.md)**

## Quick Start

```bash
poetry run iod-explorer
```

For more running options and configuration details, refer to the main documentation linked above.

## Dependencies

- **tkhtmlview** (installed automatically with Poetry)
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
