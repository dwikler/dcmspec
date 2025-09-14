"""CLI for extracting, caching, and printing DICOM IOD Module tables from Part 3.

Features:
- Download and parse DICOM IOD tables from Part 3 of the DICOM standard.
- Extract and print the list of modules for a given IOD.
- Cache the model as a JSON file for future runs and as a structured representation of the standard.
- Print the resulting module list as a table.
- Supports caching, configuration files, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.iodmodules <table_id> [options]

For more details, use the --help option.
"""

import os
import argparse
from dcmspec.config import Config

from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter


def main():
    """CLI for parsing, caching, and printing DICOM IOD Module tables.

    This CLI downloads, caches, and prints the list of modules of a given DICOM IOD (Information Object Definition)
    from Part 3 of the DICOM standard.

    The tool parses only the specified IOD table to extract the list of referenced modules, including their Information
    Entity (IE), reference, and usage. It does not parse or include the attributes of the referenced module tables.
    The output is a table listing all modules for the specified IOD.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the IOD's module composition, which can be used for further processing or
    integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the
    CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.iodmodules <table_id> [options]

    Options:
        table (str): Table ID to extract (e.g., "table_A.1-1" or "table_B.1-1").
        --config (str): Path to the configuration file.

    Example:
        poetry run python -m src.dcmspec.apps.cli.iodmodules table_A.1-1

    """
    url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    # parser.add_argument("table", help="Table ID")
    parser.add_argument("table", nargs="?", default="table_A.3-1", help="Table ID")

    parser.add_argument("--config", help="Path to the configuration file")
    args = parser.parse_args()

    cache_file_name = "Part3.xhtml"
    model_file_name = f"Part3_{args.table}.json"
    table_id = args.table 

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)

    # Initialize configuration
    config = Config(app_name="dcmspec", config_file=config_file)

    # Create the factory
    factory = SpecFactory(
        column_to_attr={0: "ie", 1: "module", 2: "ref", 3: "usage"}, 
        name_attr="module",
        config=config,
    )

    # Download, parse, and cache the model
    model = factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        json_file_name=model_file_name,
        table_id=table_id,
        force_download=False,
    )

    # Print the model as a table
    printer = SpecPrinter(model)
    printer.print_table(colorize=True)


if __name__ == "__main__":
    main()
