import os
import argparse
from dcmspec.config import Config

from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter


def main():
    url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("table", help="Table ID")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument(
        "--include-depth",
        type=int,
        default=None,
        help="Depth to which included tables should be parsed (default: unlimited)"
    )
    parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Force reparsing of the DOM and regeneration of the JSON model, even if the JSON cache exists"
    )    
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force download of the input file and regeneration of the model, even if cached"
    )
    parser.add_argument(
        "--print-mode",
        choices=["table", "tree", "none"],
        default="table",
        help="Print as 'table' (default), 'tree', or 'none' to skip printing"
    )

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
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}, 
        name_attr="elem_name",
        config=config,
    )

    # Download, parse, and cache the model
    model = factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        json_file_name=model_file_name,
        table_id=table_id,
        force_parse=args.force_parse,
        force_download=args.force_download,
        include_depth=args.include_depth,
    )

    printer = SpecPrinter(model)
    if args.print_mode == "tree":
        printer.print_tree(colorize=True)
    elif args.print_mode == "table":
        printer.print_table(colorize=True)
    # else: do not print anything if print_mode == "none"


if __name__ == "__main__":
    main()
