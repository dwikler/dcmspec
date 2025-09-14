"""CLI for extracting, caching, and printing the complete set of DICOM attributes for a given IOD from Part 3.

Features:
- Download and parse DICOM IOD tables from Part 3 of the DICOM standard.
- Automatically parse all referenced Module Attributes tables for the IOD.
- Cache the model as a JSON file for future runs and as a structured representation of the standard.
- Print the resulting attributes as a table or tree.
- Supports both Composite and Normalized IODs.
- Supports caching, configuration files, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.iodattributes <table_id> [options]

For more details, use the --help option.
"""

import os
import argparse

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.iod_spec_printer import IODSpecPrinter
from dcmspec.spec_factory import SpecFactory


def main():
    """CLI for parsing, caching, and printing DICOM IOD attribute models.

    This CLI downloads, caches, and prints all attributes for a specified DICOM IOD (Information Object Definition)
    from Part 3 of the DICOM standard, supporting both Composite and Normalized IODs.

    When an IOD table is specified, the tool parses the IOD table to determine which modules are referenced, then
    automatically parses each referenced Module Attributes table. The resulting model contains both the list of modules
    and, for each module, all its attributes. The print output (table or tree) shows only the attributes, not the IOD
    table or module structure itself.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the IOD's attributes, which can be used for further processing or integration in
    other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.iodattributes <table_id> [options]

    Options:
        table (str): Table ID to extract (e.g., "table_A.3-1" or "table_B.26.2-1").
        --config (str): Path to the configuration file.
        --print-mode (str): Print as 'table' (default), 'tree', or 'none' to skip printing.

    Example:
        poetry run python -m src.dcmspec.apps.cli.iodattributes table_A.3-1 --print-mode tree

    """
    url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("table", help="Table ID")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument(
        "--print-mode", 
        choices=["table", "tree", "none"],
        default="table",
        help="Print as 'table' (default), 'tree', or 'none' to skip printing"
    )
    args = parser.parse_args()

    cache_file_name = "Part3.xhtml"
    model_file_name = f"Part3_{args.table}_expanded.json"
    table_id = args.table 

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)

    # Initialize configuration
    config = Config(app_name="dcmspec", config_file=config_file)

    # Check table_id belongs to either Composite or Normalized IODs annexes
    if "table_A." in table_id:
        composite_iod = True
    elif "table_B." in table_id:
        composite_iod = False
    else:
        parser.error(f"table {table_id} does not correspond to a Composite or Normalized IOD")

    # Create the IOD specification factory
    c_iod_columns_mapping = {0: "ie", 1: "module", 2: "ref", 3: "usage"}
    n_iod_columns_mapping = {0: "module", 1: "ref", 2: "usage"}
    iod_columns_mapping = c_iod_columns_mapping if composite_iod else n_iod_columns_mapping
    iod_factory = SpecFactory(
        column_to_attr=iod_columns_mapping, 
        name_attr="module",
        config=config,
    )

    # Create the modules specification factory
    parser_kwargs=None if composite_iod else {"skip_columns": [2]}
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
        parser_kwargs=parser_kwargs,
        config=config,
    )

    # Create the builder
    builder = IODSpecBuilder(iod_factory=iod_factory, module_factory=module_factory)

    # Download, parse, and cache the combined model
    model, _ = builder.build_from_url(
        url=url,
        cache_file_name=cache_file_name,
        json_file_name=model_file_name,
        table_id=table_id,
        force_download=False,
    )

    # Print the model
    printer = IODSpecPrinter(model)
    if args.print_mode == "tree":
        printer.print_tree(colorize=True)
    elif args.print_mode == "table":
        printer.print_table(colorize=True)
    # else: do not print anything if print_mode == "none"

if __name__ == "__main__":
    main()
