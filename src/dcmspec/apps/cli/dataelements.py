"""CLI for extracting, caching, and printing DICOM Data Elements from Part 6.

Features:
- Download and parse DICOM Data Elements table from Part 6 of the DICOM standard.
- Cache the model as a JSON file for future runs and as a structured representation of the standard.
- Print the resulting Data Elements as a table.
- Supports caching, configuration files, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.dataelements [options]

For more details, use the --help option.
"""

import os
import argparse
from dcmspec.config import Config

from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter


def main():
    """CLI for parsing, caching, and printing DICOM Data Elements from Part 6.

    This CLI downloads, caches, and prints the list of DICOM Data Elements from Part 6 of the DICOM standard.

    The tool parses the Data Elements table to extract tags, names, keywords, VR (Value Representation),
    VM (Value Multiplicity), and status for all DICOM data elements. The output can be printed as a table.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the DICOM Data Elements, which can be used for further processing or integration
    in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.dataelements [options]

    Options:
        --config (str): Path to the configuration file.

    Example:
        poetry run python -m src.dcmspec.apps.cli.dataelements

    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to the configuration file")
    args = parser.parse_args()

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)

    # Initialize configuration
    config = Config(app_name="dcmspec", config_file=config_file)

    url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html"
    cache_file_name = "DataElements.xhtml"
    json_cache_path = "DataElements.json"
    table_id = "table_6-1"

    # Create the factory
    factory = SpecFactory(
        column_to_attr={
            0: "elem_tag",
            1: "elem_name",
            2: "elem_keyword",
            3: "elem_vr",
            4: "elem_vm",
            5: "elem_status"
        },
        config=config
    )

    # Download, parse, and cache the model
    model = factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        table_id=table_id,
        force_download=False,
        json_file_name=json_cache_path,
    )

    # Print the model as a table
    printer = SpecPrinter(model)
    printer.print_table(colorize=True)


if __name__ == "__main__":
    main()
