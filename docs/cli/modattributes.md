# modattributes

## Description

CLI for extracting, caching, and printing DICOM Module Attributes tables from Part 3 of the DICOM standard.

This CLI downloads, caches, and prints the attributes of a given DICOM Module from Part 3 of the DICOM standard. Optionally, it can enrich the module with VR, VM, Keyword, or Status information from Part 6 (Data Elements dictionary).

The tool parses the specified Module Attributes table to extract all attributes, tags, types, and descriptions for the module. Optionally, it can merge in VR, VM, Keyword, or Status information from Part 6. The output can be printed as a table or tree.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the module's attributes, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../configuration.md) page.

---

## Usage

```bash
poetry run python -m src.dcmspec.cli.modattributes <table_id> [options]
```

`<table_id>`  
: The DICOM table ID to extract (e.g., `table_C.7-1`).

`[options]`  
: Additional command-line options (see below).

## Options

`--config <file>`  
: Path to the configuration file.

`--add-part6 [VR VM Keyword Status]`  
: Specification(s) to merge from Part 6 (e.g., `--add-part6 VR VM`).

`--force-update`  
: Force update of the specifications merged from part 6, even if cached. Only applies when `--add-part6` is used.

`--print-mode <mode>`  
: Print as `'table'` (default), `'tree'`, or `'none'` to skip printing.

`--include-depth <int>`  
: Depth to which included tables should be parsed (default: unlimited).

`--force-parse`  
: Force reparsing of the DOM and regeneration of the JSON model, even if the JSON cache exists.

`--force-download`  
: Force download of the input file and regeneration of the model, even if cached. Implies `--force-parse`.

`-v`, `--verbose`  
: Enable verbose (info-level) logging to the console.

`-d`, `--debug`  
: Enable debug logging to the console (overrides `--verbose`).

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To parse the Patient Module Attributes Table and print it as a table:

```bash
poetry run python -m src.dcmspec.cli.modattributes table_C.7-1
```

To enrich the table with VR and VM information from Part 6:

```bash
poetry run python -m src.dcmspec.cli.modattributes table_C.7-1 --add-part6 VR VM
```

To print the result as a tree:

```bash
poetry run python -m src.dcmspec.cli.modattributes table_C.7-1 --print-mode tree
```
