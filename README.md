[![tests](https://github.com/dwikler/dcmspec/actions/workflows/test.yml/badge.svg)](https://github.com/dwikler/dcmspec/actions/workflows/test.yml)

# dcmspec

## Overview

**dcmspec** is a versatile toolkit designed to provide processing of DICOM specifications from the DICOM standard or IHE documents. It aims to streamline the process of parsing, extracting, and using DICOM specifications to support software developers in leveraging DICOM within their applications. It also provides CLI applications which converts parts of the DICOM standard into a structured representation.

## Features

- **Attributes Requirements Parsing from DICOM Standard**: Extract attributes requirements from tables in DICOM standard.
- **Attributes Requirements Parsing from IHE-RO TDW-II**: Extract attributes requirements from tables in IHE Technical Framework or Supplements.

## For Developers

### Installation Using Poetry

To install the package using Poetry, follow these steps:

1. **Add the following to your `pyproject.toml`**:

   ```toml
   [tool.poetry.dependencies]
   dcmspec = { git = "https://github.com/dwikler/dcmspec.git", tag = "v0.1.0" }
   ```

2. **Install the Dependencies**:
   ```bash
   poetry install
   ```

### Contributing

If you want to contribute to the project, follow these steps:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/dwikler/dcmspec.git
   cd dcmspec
   ```

2. **Install dependencies**:

   ```bash
   poetry install
   ```

3. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

## Command-Line Interface (CLI) Applications

After installing and activating your environment, you can use the CLI tools provided by **dcmspec**.

### DICOM Standard Parsers Scripts

- `dataelements`: parses Data Elements definitions from Part 6: Data Dictionary
- `uidvalues`: parses Unique Identifiers (UIDs) definitions from Part 6: Data Dictionary
- `modattributes`: parses Module Attributes specification from Part 3: Information Object Definitions
- `upsattributes`: parses UPS Attributes specification from Part 4: Service Class Specifications

The DICOM Standards documents and their structured data models will be saved in the default cache folder or in a folder you define using the configuration file.

```json
{
  "cache_dir": "./cache"
}
```

The config file can be created as config.json in the default configuration folder or its location can be specified using the --config option or using the `DCMSPEC_CONFIG` environment variable.

The default cache and configuration folders location depends on the platform.

MacOS:

- Default cache folder: ~/Library/Caches/dcmspec
- Default configuration folder: ~/Library/Application Support/dcmspec

Linux:

- Default cache folder: ~/.cache/dcmspec
- Default configuration folder: ~/.config/dcmspec

Windows:

- Default cache folder: %USERPROFILE%\AppData\Local\dcmspec\Cache
- Default configuration folder: %USERPROFILE%\AppData\Local\dcmspec or %USERPROFILE%\AppData\Roaming\dcmspec

~/.cache/dcmspec

### Example: Parsing a DICOM IOD Module Attributes Table

To parse the Part 6 Data Elements table and print it as an ASCII table,

- **run the CLI app module as a script:**

  ```bash
  poetry run python -m src.dcmspec.cli.dataelements
  ```

- **run the script directly using the registered entry point**  
  (see `[tool.poetry.scripts]` in `pyproject.toml`)

  ```bash
  poetry run dataelements
  ```

- **run the CLI app module as a script directly (without Poetry):**

  ```bash
  export PYTHONPATH=$(pwd)/src
  source ./.venv/bin/activate
  python -m dcmspec.cli.dataelements
  ```
