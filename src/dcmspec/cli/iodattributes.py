import os
import argparse

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.iod_spec_printer import IODSpecPrinter
from dcmspec.spec_factory import SpecFactory


def main():
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
        print(f"table {table_id} does not correspond to a Composite or Normalized IOD")
        exit(1)

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
    model = builder.build_from_url(
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
