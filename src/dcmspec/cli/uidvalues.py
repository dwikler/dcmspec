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

    url = "https://dicom.nema.org/medical/dicom/current/output/html/part06.html"
    cache_file_name = "Part6.xhtml"
    model_file_name = "UIDValues.json"

    table_id = "table_A-1"

    # Create the factory
    factory = SpecFactory(
        column_to_attr={0: "uid_value", 1: "uid_name", 2: "uid_keyword", 3: "uid_type", 4: "uid_part"},
        name_attr="uid_value",
        config=config
    )

    # Download, parse, and cache the model
    model = factory.from_url(
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
