# upsioddimseattributes

## Description

CLI for extracting, merging, caching, and printing DICOM UPS IOD attributes aligned with DIMSE service requirements from Part 3 and Part 4 of the DICOM standard.

This CLI downloads, merges, caches, and prints the attributes for a DICOM UPS IOD (Unified Procedure Step Information Object Definition) from Part 3, aligned with the requirements of a selected DIMSE service and role from Part 4. The tool parses the IOD table and all referenced module attribute tables, then merges in the UPS DIMSE service requirements (e.g., N-CREATE, N-SET, N-GET, C-FIND, FINAL) and role (SCU or SCP) from Part 4. The output can be printed as a table or tree.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the merged IOD and DIMSE service attributes, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.cli.upsioddimseattributes [options]

`[options]`  
: Additional command-line options (see below).

## Options

`--config <file>`  
: Path to the configuration file.

`--dimse <service>`  
: DIMSE service to use (e.g., `ALL_DIMSE`, `N-CREATE`, `N-SET`, `N-GET`, `C-FIND`, `FINAL`). Default: `ALL_DIMSE`.

`--role <role>`  
: DIMSE role to use (`SCU` or `SCP`).

`--print-mode <mode>`  
: Print as `'table'` (default), `'tree'`, or `'none'` to skip printing.

`-v`, `--verbose`  
: Enable verbose (info-level) logging to the console.

`-d`, `--debug`  
: Enable debug logging to the console (overrides `--verbose`).

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To print the merged UPS IOD attributes for all DIMSE services as a table:

    poetry run python -m src.dcmspec.cli.upsioddimseattributes

To print only the N-CREATE service attributes for the SCU role as a tree:

    poetry run python -m src.dcmspec.cli.upsioddimseattributes --dimse N-CREATE --role SCU --print-mode tree
