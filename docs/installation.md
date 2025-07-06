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

See the [API Reference](./api/index.md) for details on available classes.
