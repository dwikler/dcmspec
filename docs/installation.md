# Installation

## Prerequisites

- Python 3.8 or newer
- [Poetry](https://python-poetry.org/) (optional for CLI users, recommended for developers)

---

## For Users of CLI Applications

- Install with pip (recommended for CLI use):

  To install from PyPI:

  ```bash
  pip install dcmspec
  ```

  Or, for the latest development version from GitHub:

  ```bash
  pip install "git+https://github.com/dwikler/dcmspec.git@main"
  ```

- Alternatively, install with Poetry (requires cloning the repo):

  ```bash
  git clone https://github.com/dwikler/dcmspec.git
  cd dcmspec
  poetry install
  ```

- Run CLI applications (replace `<script_name>` with one of the following):

  ```bash
  python -m dcmspec.apps.cli.<script_name> --help
  ```

  Examples:

  ```bash
  python -m dcmspec.apps.cli.iodattributes --help
  python -m dcmspec.apps.cli.tdwiimoddefinition --help
  ```

  Or, if using Poetry:

  ```bash
  poetry run python -m dcmspec.apps.cli.<script_name> --help
  ```

  See the [CLI Applications](./apps/cli/index.md) for available scripts and usage examples.

---

## For Users of the GUI Application

- Install the package with the GUI extra (installs `tkhtmlview`):

  To install from **PyPI** (recommended for most users):

  ```bash
  pip install "dcmspec[gui]"
  ```

  Or, for the latest development version from GitHub (for advanced users or contributors):

  ```bash
  pip install "git+https://github.com/dwikler/dcmspec.git@main#egg=dcmspec[gui]"
  ```

  Or, with Poetry from PyPI (recommended for most users):

  ```bash
  poetry add "dcmspec[gui]"
  ```

  Or, for the latest development version from GitHub (for advanced users or contributors):

  ```bash
  poetry add "dcmspec[gui]"@git+https://github.com/dwikler/dcmspec.git
  ```

  Or, for local development or contributing (using Poetry):

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
  poetry run iod-explorer
  ```

  Or, after activating your environment:

  ```bash
  iod-explorer
  ```

---

## For Developers Using the API

- Add the following to your `pyproject.toml` (for Poetry-based projects):

  ```toml
  [tool.poetry.dependencies]
  dcmspec = "^0.2.1"
  ```

  (Optional) To use the latest development version from GitHub:

  ```toml
  [tool.poetry.dependencies]
  dcmspec = { git = "https://github.com/dwikler/dcmspec.git", branch = "main" }
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

> **Note on lxml:**  
> `lxml` is a core dependency for fast and robust XML/HTML parsing. It is not a pure Python package, but pre-built wheels are available for most platforms.  
> On some Linux systems, you may need to install system packages (e.g., `libxml2-dev`, `libxslt-dev`, and `python3-dev`) before installing `lxml`.  
> See the [lxml installation docs](https://lxml.de/installation.html) for details.

### Optional PDF/Table Extraction Dependencies

Some features, such as extracting tables directly from PDF files, require additional heavy dependencies. These are **not installed by default** and are grouped under the `pdf` optional dependency.

To install with PDF/table extraction support from PyPI:

Using pip:

```bash
pip install "dcmspec[pdf]"
```

Or, for the latest development version from GitHub:

```bash
pip install "git+https://github.com/dwikler/dcmspec.git@main#egg=dcmspec[pdf]"
```

Or, using Poetry:

```bash
poetry add "dcmspec[pdf]"
```

Or, for the latest development version from GitHub:

```bash
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

Using pip from PyPI:

```bash
pip install "dcmspec[gui]"
```

Or, with Poetry from PyPI:

```bash
poetry add "dcmspec[gui]"
```

Or, for the latest development version from GitHub:

```bash
poetry add "dcmspec[gui]"@git+https://github.com/dwikler/dcmspec.git
```

This will install:

- tkhtmlview

### Summary

- Default install: Lightweight, core parsing features only.
- With `[pdf]` extra: Adds PDF/table extraction support.
- With `[gui]` extra: Adds GUI dependencies for the sample explorer app.
- You can combine extras, e.g., pip install "dcmspec[gui,pdf]".
  See the pyproject.toml for the full list of dependencies and extras.

See the [API Reference](./api/index.md) for details on available classes.
