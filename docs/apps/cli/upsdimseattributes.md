# upsdimseattributes

## Description

CLI for extracting, caching, and printing DICOM UPS (Unified Procedure Step) DIMSE Service Attribute tables from Part 4 of the DICOM standard.

This CLI downloads, caches, and prints the attributes for the UPS DIMSE services from Part 4 of the DICOM standard. The tool parses the UPS Service Attribute table and allows selection of a specific DIMSE service (e.g., N-CREATE, N-SET, N-GET, C-FIND, FINAL) and role (SCU or SCP). The output can be printed as a table.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the UPS DIMSE service attributes, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.apps.cli.upsdimseattributes [options]

`[options]`  
: Additional command-line options (see below).

## Options

`--config <file>`  
: Path to the configuration file.

`--dimse <service>`  
: DIMSE service to select (`ALL_DIMSE`, `N-CREATE`, `N-SET`, `N-GET`, `C-FIND`, `FINAL`). Default: `ALL_DIMSE`.

`--role <role>`  
: Role to select (`SCU` or `SCP`). Only valid if `--dimse` is not `ALL_DIMSE`.

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To print all UPS DIMSE service attributes as a table:

    poetry run python -m src.dcmspec.apps.cli.upsdimseattributes

To print only the N-CREATE service attributes for the SCU role:

    poetry run python -m src.dcmspec.apps.cli.upsdimseattributes --dimse N-CREATE --role SCU
