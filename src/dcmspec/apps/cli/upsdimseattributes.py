"""CLI for extracting, caching, and printing DICOM UPS DIMSE Service Attribute tables from Part 4.

Features:
- Download and parse UPS DIMSE Service Attribute table from Part 4 of the DICOM standard.
- Select a specific DIMSE service and role for filtering.
- Cache the model as a JSON file for future runs and as a structured representation of the standard.
- Print the resulting attributes as a table.
- Supports caching, configuration files, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.upsdimseattributes [options]

For more details, use the --help option.
"""

import os
import argparse
from dcmspec.config import Config

from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler
from dcmspec.service_attribute_defaults import UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR


def main():
    """CLI for parsing, caching, and printing DICOM UPS DIMSE Service Attribute tables from Part 4.

    This CLI downloads, caches, and prints the attributes for the UPS DIMSE services from Part 4 of the DICOM standard.

    The tool parses the UPS Service Attribute table and allows selection of a specific DIMSE service (e.g., N-CREATE,
    N-SET, N-GET, C-FIND, FINAL) and role (SCU or SCP). The output can be printed as a table.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the UPS DIMSE service attributes, which can be used for further processing or
    integration in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the
    CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.upsdimseattributes [options]

    Options:
        --config (str): Path to the configuration file.
        --dimse (str): DIMSE service to select (ALL_DIMSE, N-CREATE, N-SET, N-GET, C-FIND, FINAL).
        --role (str): Role to select (SCU or SCP). Only valid if --dimse is not ALL_DIMSE.

    Example:
        poetry run python -m src.dcmspec.apps.cli.upsdimseattributes --dimse N-CREATE --role SCU

    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument(
        "--dimse",
        choices=["ALL_DIMSE", "N-CREATE", "N-SET", "N-GET", "C-FIND", "FINAL"],
        default="ALL_DIMSE",
        help="DIMSE service to select (default: ALL_DIMSE)",
    )
    parser.add_argument(
        "--role",
        choices=["SCU", "SCP"],
        help="Role to select (SCU or SCP)",
    )
    args = parser.parse_args()

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)
    
    # Initialize configuration
    config = Config(app_name="dcmspec", config_file=config_file)

    url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_CC.2.5.html"
    cache_file_name = "UPSattributes.xhtml"
    table_id = "table_CC.2.5-3"  
    
    # Create the factory with UPSXHTMLDocHandler for UPS-specific table patching
    factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(config=config),
        column_to_attr=UPS_COLUMNS_MAPPING,
        name_attr=UPS_NAME_ATTR,
        config=config
    )

    # Download, parse, and cache the model
    model = factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        table_id=table_id,
        force_download=False,
        model_kwargs={"dimse_mapping": UPS_DIMSE_MAPPING},
    )

    if args.dimse!= "ALL_DIMSE":
        model.select_dimse(args.dimse)
    if args.role:
        if args.dimse == "ALL_DIMSE":
            parser.error("--role option can only be used if --dimse is not ALL_DIMSE")
        model.select_role(args.role)

    # Print the model as a table
    printer = SpecPrinter(model)
    printer.print_table(colorize=True)


if __name__ == "__main__":
    main()
