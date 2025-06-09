import os
import argparse
from dcmspec.config import Config

from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler


def main():
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
    UPS_DIMSE_MAPPING = {
    "ALL_DIMSE": {
        2: "dimse_ncreate", 
        3: "dimse_nset", 
        4: "dimse_final", 
        5: "dimse_nget", 
        6: "key_matching", 
        7: "key_return", 
        8: "type_remark"
        },
    "N-CREATE": {2: "dimse_ncreate", 8: "type_remark"},
    "N-SET": {3: "dimse_nset", 8: "type_remark"},
    "N-GET": {5: "dimse_nget", 8: "type_remark"},
    "C-FIND": {6: "key_matching", 7: "key_return", 8: "type_remark"},
    "FINAL": {4: "dimse_final", 8: "type_remark"},
    }
    # Create the factory with UPSXHTMLDocHandler for UPS-specific table patching
    factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(config=config),
        column_to_attr=columns_mapping,
        name_attr="elem_name",
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

    if args.dimse:
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
