# tdwiimoddefinition

## Description

CLI for extracting and printing the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement.

This CLI downloads, parses, and prints the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement (PDF). The tool extracts the relevant table(s) from the PDF, parses the module definition, and outputs the result as a table and a tree.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured, machine-readable representation of the module definition, which can be used for further processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../configuration.md) page.

---

## Usage

    poetry run python -m src.dcmspec.cli.tdwiimoddefinition [options]

`[options]`  
: Additional command-line options (see below).

## Options

`-d`, `--debug`  
: Enable debug logging.

`-v`, `--verbose`  
: Enable verbose output.

`-h`, `--help`  
: Show this help message and exit.

---

## Examples

To extract and print the TDW-II UPS Scheduled Info Base table:

    poetry run python -m src.dcmspec.cli.tdwiimoddefinition
