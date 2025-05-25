import os
import argparse
from dcmspec.config import Config

from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter


def main():
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
        column_to_attr={0: "elem_tag", 1: "elem_name", 2: "elem_keyword", 3: "elem_vr", 4: "elem_vm", 5: "elem_status"}, 
        config=config
    )

    # Download, parse, and cache the model
    model = factory.from_url(
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
