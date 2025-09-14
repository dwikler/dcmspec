# tdwiicontent

## Description

CLI for extracting and printing the TDW-II profile content definitions from the IHE-RO TDW-II Supplement.

This CLI downloads, parses, and prints the TDW-II content definition tables from the TDW-II IHE-RO Supplement
in PDF format.
The tool extracts the relevant table(s) for the selected content definition, parses the module definition, and
outputs the result as a table and a tree.

The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
machine-readable representation of the content definition, which can be used for further processing or integration
in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

For more information on configuration and caching location see the [Configuration and Caching](../../configuration.md)
page.

---

## Usage

    poetry run python -m src.dcmspec.apps.cli.tdwiicontent <content_definition> [options]

`<content_definition>`  
: Required positional argument. One of:

- `ups_create`: content of scheduled UPS creation (combined UPS Scheduled and Relationship definitions)
- `ups_query`: content of C-FIND identifier for UPS Query transaction
- `ups_progress`: content of N-SET dataset for UPS Progress Update transaction
- `ups_performed`: content of N-SET dataset for UPS Final Status Update transaction
- `rt_bdi`: content of RT Beam Delivery Instruction Module

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

To extract and print the TDW-II Progress Update transaction UPS content specification:

    poetry run python -m src.dcmspec.apps.cli.tdwiicontent ups_progress --debug

To extract and print the RT Beam Delivery Instruction Module definition:

    poetry run python -m src.dcmspec.apps.cli.tdwiicontent rt_bdi
