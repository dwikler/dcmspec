# Installation

## Table of Contents

- [Prerequisites](#prerequisites)
- [Sample Application Users](#sample-application-users)
- [API Users](#api-users)
- [Contributors](#contributors)
- [Dependencies and Optional Features](#dependencies-and-optional-features)
- [Python Installation](#python-installation)
- [Tkinter Installation](#tkinter-installation)
- [Poetry Installation](#poetry-installation)

## Prerequisites

- **Python 3.9.2 or newer**

  - See [Python installation](#python-installation) for platform-specific instructions.

- **tkinter** (optional, only required for the GUI sample application)

  - Part of the Python standard library, but may require extra steps to install on some platforms. See [Tkinter installation](#tkinter-installation) for details.

- **pip** (optional, required only for pip-based installation)

  - Comes with Python and is recommended for most users.

- **[Poetry](https://python-poetry.org/)** (optional, required only for Poetry-based installation)
  - Recommended for contributors and for developers who use Poetry in their own projects. See [Poetry installation instructions](#poetry-installation) for how to install Poetry itself.
    > **Note:** You must have at least one of `pip` or `poetry` installed to install dcmspec.

---

## Sample Application Users

### Install from PyPI (recommended for all sample applications, CLI and GUI)

```bash
pip install "dcmspec[gui]"
```

> If you get an error about `tkinter`, see [Tkinter installation](#tkinter-installation).

### Run CLI applications

```bash
<command> --help
```

Where `<command>` is one of the available CLI scripts, e.g.:

```bash
iodattributes --help
tdwiimoddefinition --help
```

Alternatively, you can use:

```bash
python -m dcmspec.apps.cli.<script_name> --help
```

See the [CLI Applications](./apps/cli/index.md) for available commands and usage examples.

### Run the GUI application

```bash
iod-explorer
```

See the [UI Applications](./apps/ui/index.md) for more information.

<sub>[Back to top](#table-of-contents)</sub>

---

## API Users

> **Tip:** If you use Poetry to manage your own project, you can skip the pip instructions below and go directly to [Add to your Poetry project](#add-to-your-poetry-project).
>
> See [Dependencies and Optional Features](#dependencies-and-optional-features) below for details on core vs extra dependencies versions.

### Using pip

#### Install core (lightweight) version from PyPI

```bash
pip install dcmspec
```

#### Install with PDF/table extraction support

```bash
pip install "dcmspec[pdf]"
```

#### Install with GUI support

```bash
pip install "dcmspec[gui]"
```

#### Install with both PDF and GUI support

```bash
pip install "dcmspec[gui,pdf]"
```

#### (Optional) To use the latest development version from GitHub

```bash
pip install "git+https://github.com/dwikler/dcmspec.git@main"
```

### Using Poetry

#### Add to your Poetry project

If you are using Poetry to manage your own project, add dcmspec as a dependency with the desired optional features:

```bash
poetry add dcmspec              # core only
poetry add "dcmspec[gui]"       # with GUI support
poetry add "dcmspec[pdf]"       # with PDF support
poetry add "dcmspec[gui,pdf]"   # with both
```

#### (Optional) To use the latest development version from GitHub

```bash
poetry add "dcmspec@git+https://github.com/dwikler/dcmspec.git"
```

---

### Import and use the API

```python
from dcmspec.spec_model import SpecModel
# ... your code here ...
```

<sub>[Back to top](#table-of-contents)</sub>

---

## Contributors

## Contributors

For contributor installation and development instructions, see the [CONTRIBUTING.md](https://github.com/dwikler/dcmspec/blob/main/CONTRIBUTING.md){:target="\_blank"} on GitHub.

<sub>[Back to top](#table-of-contents)</sub>

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

<sub>[Back to top](#table-of-contents)</sub>

## Python Installation

- You can check your version with:
  ```bash
  python3 --version
  ```
- On macOS, you can install Python with [Homebrew](https://brew.sh/) or from [python.org](https://www.python.org/downloads/).
- On Linux, use your system package manager (e.g., `sudo apt install python3`).
- On Windows, use the [python.org](https://www.python.org/downloads/) installer.

<sub>[Back to top](#table-of-contents)</sub>

## Tkinter Installation

tkinter is the Python interface to the Tcl/Tk GUI toolkit. On some platforms, installing tkinter will also install the required tcl-tk libraries.

- **macOS (Homebrew Python):**

  - Install Python if not present yet. (Commands below are for Python 3.9, replace `3.9` with your Python version if needed).
    ```bash
    brew install python@3.9
    ```
  - Then, install tkinter support:
    ```bash
    brew install python-tk@3.9
    ```
  - For Python 3.10, 3.11, 3.12, use the matching `python-tk@<version>` formula, e.g.:
    ```bash
    brew install python-tk@3.12
    ```

- **Windows or macOS (python.org installer):**  
  `tkinter` is usually included by default.
- **Ubuntu/Debian:**  
  Install with `sudo apt install python3-tk`

After installation, you can test if `tkinter` is available by running:

```bash
python3 -m tkinter
```

If a small window appears, `tkinter` is working.

For more details, see the [Homebrew Python and Tkinter documentation](https://docs.brew.sh/Homebrew-and-Python#tkinter) and the [python-tk Homebrew formulae](https://formulae.brew.sh/formula/python-tk@3.12).

<sub>[Back to top](#table-of-contents)</sub>

## Poetry Installation

- Install with [pipx](https://pypa.github.io/pipx/):

  - **macOS (Homebrew):**
    ```bash
    brew install pipx
    pipx ensurepath
    pipx install poetry
    ```
  - **Linux/Windows:**
    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install poetry
    ```
  - **Windows:**
    1. Open "Command Prompt" or "PowerShell" as administrator.
    2. Run:
       ```cmd
       python -m pip install --user pipx
       python -m pipx ensurepath
       pipx install poetry
       ```
    3. Close and reopen your terminal to update your PATH.

- For more details or troubleshooting, refer to the [Poetry installation guide](https://python-poetry.org/docs/#installation).

<sub>[Back to top](#table-of-contents)</sub>
