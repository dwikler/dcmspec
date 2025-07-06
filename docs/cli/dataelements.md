# dataelements

## Description

CLI for extracting, caching, and printing DICOM Data Elements from Part 6 of the DICOM standard.

This CLI downloads, caches, and prints the list of DICOM Data Elements from Part 6 of the DICOM standard. The tool parses the Data Elements table to extract tags, names, keywords, VR (Value Representation), VM (Value Multiplicity), and status for all DICOM data elements. The output can be printed as a table or tree.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the DICOM Data Elements, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.cli.dataelements [options]

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

To print the DICOM Data Elements as a table:

    poetry run python -m src.dcmspec.cli.dataelements

To print the DICOM Data Elements as a tree:

    poetry run python -m src.dcmspec.cli.dataelements --print-mode tree
