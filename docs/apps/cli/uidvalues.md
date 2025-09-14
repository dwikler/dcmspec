# uidvalues

## Description

CLI for extracting, caching, and printing DICOM Unique Identifiers (UIDs) from Part 6 of the DICOM standard.

This CLI downloads, caches, and prints the list of DICOM UIDs from Part 6 of the DICOM standard. The tool parses the UID Values table to extract UID values, names, types, and additional information. The output can be printed as a table.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the DICOM UIDs, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.apps.cli.uidvalues [options]

`[options]`  
: Additional command-line options (see below).

## Options

`--config <file>`  
: Path to the configuration file.

`--print-mode <mode>`  
: Print as `'table'` (default), `'tree'`, or `'none'` to skip printing.

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To print the DICOM UID Values as a table:

    poetry run python -m src.dcmspec.apps.cli.uidvalues

To print the DICOM UID Values as a tree:

    poetry run python -m src.dcmspec.apps.cli.uidvalues --print-mode tree
