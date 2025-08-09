# Installation

## Prerequisites

- Python 3.8 or newer
- [Poetry](https://python-poetry.org/) (optional for CLI users, recommended for developers)

---

## For Users of CLI Applications

- Install with pip (recommended for CLI use):

  ```bash
  pip install "git+https://github.com/dwikler/dcmspec.git@v0.1.0"
  ```

- Alternatively, install with Poetry (requires cloning the repo):

  ```bash
  git clone https://github.com/dwikler/dcmspec.git
  cd dcmspec
  poetry install
  ```

- Run CLI applications (replace `<script_name>` with one of the following):

  ```bash
  python -m dcmspec.cli.<script_name> --help
  ```

  Examples:

  ```bash
  python -m dcmspec.cli.iodattributes --help
  python -m dcmspec.cli.tdwiimoddefinition --help
  ```

  Or, if using Poetry:

  ```bash
  poetry run python -m src.dcmspec.cli.<script_name> --help
  ```

  See the [CLI Applications](./cli/index.md) for available scripts and usage examples.

---

## For Users of the GUI Application

- Install the package with the GUI extra (installs `tkhtmlview`):

  ```bash
  pip install "git+https://github.com/dwikler/dcmspec.git@v0.1.0#egg=dcmspec[gui]"
  ```

  Or, with Poetry:

  ```bash
  git clone https://github.com/dwikler/dcmspec.git
  cd dcmspec
  poetry install --with gui
  ```

- **tkinter** is also required for the GUI, but is not installed via pip or Poetry.

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

- Run the GUI application:

  ```bash
  poetry run dcmspec-explorer
  ```

  Or, after activating your environment:

  ```bash
  dcmspec-explorer
  ```

---

## For Developers Using the API

- Add the following to your `pyproject.toml` (for Poetry-based projects):

  ```toml
  [tool.poetry.dependencies]
  dcmspec = { git = "https://github.com/dwikler/dcmspec.git", tag = "v0.1.0" }
  ```

- Install the dependencies:

  ```bash
  poetry install
  ```

- (Optional) Activate the virtual environment:

  ```bash
  poetry shell
  ```

- Import and use the API in your Python code:

  ```python
  from dcmspec.spec_model import SpecModel

  # ... your code here ...
  ```

---

## Dependencies and Optional Features

### Core Dependencies

The core `dcmspec` library is designed to be lightweight and only requires a minimal set of dependencies for parsing and working with DICOM specification tables in HTML/XHTML format.

Core dependencies include:

- anytree
- platformdirs
- unidecode
- bs4 (BeautifulSoup)
- requests
- lxml
- rich

These are sufficient for most use cases, including all parsing and tree-building from DICOM standard HTML/XHTML documents.

### Optional PDF/Table Extraction Dependencies

Some features, such as extracting tables directly from PDF files, require additional heavy dependencies. These are **not installed by default** and are grouped under the `pdf` optional dependency.

To install with PDF/table extraction support:

```
poetry add "dcmspec[pdf]"@git+https://github.com/dwikler/dcmspec.git
```

Optional dependencies for PDF/table extraction:

- pdfplumber
- camelot-py
- pandas
- openpyxl
- opencv-python-headless

These are only needed if you want to extract tables from PDF documents.

### GUI Dependencies

If you want to use the sample GUI explorer app, you can install the `gui` extra:

```
poetry add "dcmspec[gui]"@git+https://github.com/dwikler/dcmspec.git
```

This will install:

- tkhtmlview

### Summary

- Default install: Lightweight, core parsing features only.
- With `[pdf]` extra: Adds PDF/table extraction support.
- With `[gui]` extra: Adds GUI dependencies for the sample explorer app.

See the pyproject.toml for the full list of dependencies and extras.

See the [API Reference](./api/index.md) for details on available classes.
