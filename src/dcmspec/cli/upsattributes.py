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

    url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_CC.2.5.html"
    cache_file_name = "UPSattributes.xhtml"
    table_id = "table_CC.2.5-3"  
    columns_mapping = {
        0: "elem_name",
        1: "elem_tag",
        2: "dimse_ncreate",
        3: "dimse_nset",
        4: "dimse_final",
        5: "dimse_nget",
        6: "key_matching",
        7: "key_return",
        8: "type_remark",
    }
    # Create the factory
    factory = SpecFactory(
        column_to_attr=columns_mapping,
        name_attr="elem_name",
        config=config
    )

    # Download, parse, and cache the model
    model = factory.from_url(
        url=url,
        cache_file_name=cache_file_name,
        table_id=table_id,
        force_download=False,
    )

    # Print the model as a table
    printer = SpecPrinter(model)
    printer.print_table(colorize=True)


if __name__ == "__main__":
    main()
