# CLI Applications Overview

This section documents the sample command-line interface (CLI) applications provided by **dcmspec**.

These sample CLI applications enable extraction, parsing, and processing of specification tables and related data from the DICOM standard and IHE documents. Each CLI script is located in the `src/dcmspec/apps/cli/` folder and can be run as a standalone application.

- [modattributes](modattributes.md) (Module Attributes tables from Part 3)
- [iodattributes](iodattributes.md) (Complete set of attributes for a given IOD from Part 3)
- [iodmodules](iodmodules.md) (IOD Module tables from Part 3)
- [dataelements](dataelements.md) (Data Elements from Part 6)
- [uidvalues](uidvalues.md) (Unique Identifiers (UIDs) from Part 6)
- [upsdimseattributes](upsdimseattributes.md) (UPS DIMSE Service Attribute tables from Part 4)
- [upsioddimseattributes](upsioddimseattributes.md) (UPS IOD attributes from Part 3 and Part 4)
- [tdwiicontent](tdwiicontent.md) (TDW-II Content Specification from the IHE-RO Supplement)

## How to Run

CLI scripts can be executed using one of the following methods:

- **With Poetry:**

  ```bash
  poetry run python -m src.dcmspec.apps.cli.<script_name> --help
  ```

- **Directly (if installed as a script):**

  ```bash
  poetry run <script_name> --help
  ```

- **With Python (after setting PYTHONPATH):**
  ```bash
  export PYTHONPATH=$(pwd)/src
  python -m dcmspec.apps.cli.<script_name> --help
  ```

## Example

To parse the Patient Module Attributes Table:

```bash
poetry run python -m src.dcmspec.apps.cli.modattributes table_C.7-1
```
