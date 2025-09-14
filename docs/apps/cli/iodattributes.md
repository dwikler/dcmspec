# iodattributes

## Description

CLI for extracting, caching, and printing the complete set of DICOM attributes for a given IOD (Information Object Definition) from Part 3 of the DICOM standard.

This CLI downloads, caches, and prints all attributes for a specified DICOM IOD, supporting both Composite and Normalized IODs. When an IOD table is specified, the tool parses the IOD table to determine which modules are referenced, then automatically parses each referenced Module Attributes table. The resulting model contains both the list of modules and, for each module, all its attributes. The print output (table or tree) shows only the attributes, not the IOD table or module structure itself.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the IOD and its modules' attributes, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.apps.cli.iodattributes <table_id> [options]

`<table_id>`  
: The DICOM IOD table ID to extract (e.g., `table_A.1-1` for Composite IODs or `table_B.1-1` for Normalized IODs).

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

To parse a Composite IOD table and print it as a table:

    poetry run python -m src.dcmspec.apps.cli.iodattributes table_A.1-1

To parse a Normalized IOD table and print it as a tree:

    poetry run python -m src.dcmspec.apps.cli.iodattributes table_B.1-1 --print-mode tree
