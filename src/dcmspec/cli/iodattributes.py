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
    parser.add_argument("table", nargs="?", default="table_A.3-1", help="Table ID")
    parser.add_argument("--config", help="Path to the configuration file")
    args = parser.parse_args()

    cache_file_name = "Part3.xhtml"
    model_file_name = f"Part3_{args.table}_expanded.json"
    table_id = args.table 

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)

    # Initialize configuration
    config = Config(app_name="dcmspec", config_file=config_file)

    # Create the IOD and module factories
    iod_factory = SpecFactory(
        column_to_attr={0: "ie", 1: "module", 2: "ref", 3: "usage"}, 
        name_attr="module",
        config=config,
    )
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
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

    # Print the model as a table
    printer = IODSpecPrinter(model)
    printer.print_table(colorize=True)


if __name__ == "__main__":
    main()
