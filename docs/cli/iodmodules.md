# iodmodules

## Description

CLI for extracting, caching, and printing DICOM IOD Module tables from Part 3 of the DICOM standard.

This CLI downloads, caches, and prints the list of modules of a given DICOM IOD (Information Object Definition) from Part 3 of the DICOM standard.

The tool parses only the specified IOD table to extract the list of referenced modules, including their Information Entity (IE), reference, and usage. It does not parse or include the attributes of the referenced module tables. The output is a table listing all modules for the specified IOD.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the IOD's module composition, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.cli.iodmodules <table_id> [options]

`<table_id>`  
: The DICOM IOD table ID to extract (e.g., `table_A.1-1` for Composite IODs or `table_B.1-1` for Normalized IODs).

`[options]`  
: Additional command-line options (see below).

## Options

`--config <file>`  
: Path to the configuration file.

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To parse a Composite IOD table and print its module list as a table:

    poetry run python -m src.dcmspec.cli.iodmodules table_A.1-1

To parse a Normalized IOD table and print its module list as a table:

    poetry run python -m src.dcmspec.cli.iodmodules table_B.1-1
