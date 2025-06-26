import argparse
import logging
import os

from anytree import PreOrderIter
from dcmspec.config import Config
from dcmspec.dom_table_spec_parser import DOMTableSpecParser
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_merger import SpecMerger
from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.spec_model import SpecModel
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler
from dcmspec.service_attribute_defaults import UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR
from dcmspec.spec_printer import SpecPrinter
from dcmspec.json_spec_store import JSONSpecStore


def dicom_service_default_type(node, merged_model, service_model, default_attr, default_value):    
    # Look for "All other Attributes of ..." or "All Attributes of ..." in the service model
    parent = node.parent
    while parent is not None and parent.name != "content":
        parent_name = getattr(parent, "elem_name", parent.name)
        for svc_node in service_model.content.descendants:
            svc_name = getattr(svc_node, "elem_name", None)
            if svc_name and (
                svc_name == f"All other Attributes of {parent_name}"
                or svc_name == f"All Attributes of {parent_name}"
            ):
                return getattr(svc_node, default_attr, default_value)
        parent = parent.parent
    return default_value

def align_type_with_dimse_req(model, dimse_req_attributes, dimse_attributes):
    if not dimse_req_attributes:
        dimse_req_attr = dimse_attributes[0]  # Handle ALL_DIMSE case
    else:
        dimse_req_attr = dimse_req_attributes[0]  # Handle C-FIND case
    for node in PreOrderIter(model.content):
        # Remove elem_type from all non-attribute nodes (e.g., modules)
        if hasattr(node, "elem_type") and not (hasattr(node, "elem_name") and hasattr(node, "elem_tag")):
            delattr(node, "elem_type")
        # The rest of your logic remains unchanged
        elif hasattr(node, dimse_req_attr):
            if hasattr(node, "elem_type"):
                delattr(node, "elem_type")
        elif hasattr(node, "elem_type"):
            if dimse_req_attributes:
                setattr(node, dimse_req_attr, getattr(node, "elem_type"))
            else:
                setattr(node, "dimse_all", getattr(node, "elem_type"))
            delattr(node, "elem_type")

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dimse", default="ALL_DIMSE", help="DIMSE service to use (e.g. N-CREATE, N-SET, N-GET, etc.)")
    parser.add_argument("--role", help="DIMSE role to use (e.g. SCU, SCP)")
    args = parser.parse_args()

    # --- Build the IOD Spec Model (model 1) ---
    iod_url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
    iod_cache_file = "Part3.xhtml"
    iod_table_id = "table_B.26.2-1"
    iod_model_file = "Part3_table_B.26.2-1_expanded.json"

    config = Config(app_name="dcmspec")

    # Set up a DEBUG level logger to pass to all classes
    logger = logging.getLogger("nioddimse")
    logger.handlers.clear()  # Remove any existing handlers to avoid duplicate logs
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    iod_factory = SpecFactory(
        column_to_attr={0: "module", 1: "ref", 2: "usage"},
        name_attr="module",
        config=config,
        logger=logger
    )
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
        parser_kwargs={"skip_columns": [2]},
        config=config,
        logger=logger
    )
    builder = IODSpecBuilder(iod_factory=iod_factory, module_factory=module_factory, logger=logger)
    iod_model = builder.build_from_url(
        url=iod_url,
        cache_file_name=iod_cache_file,
        json_file_name=iod_model_file,
        table_id=iod_table_id,
        force_download=False,
    )

    # --- Build the UPS Attribute Spec Model (model 2) ---
    ups_url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_CC.2.5.html"
    ups_cache_file = "UPSattributes.xhtml"
    json_file_name = "UPSattributes.json"
    ups_table_id = "table_CC.2.5-3"

    ups_factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(config=config),
        table_parser=DOMTableSpecParser(logger=logger),
        column_to_attr=UPS_COLUMNS_MAPPING,
        name_attr=UPS_NAME_ATTR,
        config=config,
        logger=logger
    )
    ups_model = ups_factory.create_model(
        url=ups_url,
        cache_file_name=ups_cache_file,
        table_id=ups_table_id,
        force_download=False,
        json_file_name=json_file_name,
        model_kwargs={"dimse_mapping": UPS_DIMSE_MAPPING},
    )
    ups_model.select_dimse(args.dimse)    
    ups_model.select_role(args.role)

    # --- Merge by path with DICOM service default type logic ---

    # Use UPS_DIMSE_MAPPING to get the attributes to merge for the selected DIMSE
    dimse_info = UPS_DIMSE_MAPPING.get(args.dimse, {})
    dimse_attributes = dimse_info.get("attributes", [])
    dimse_req_attributes = dimse_info.get("req_attributes", [])
    # Add "comment" to the end of the list
    dimse_attributes.append("comment")

    merger = SpecMerger(config=config, logger=logger)
    merged_model = merger.merge_path_with_default(
        iod_model,
        ups_model,
        merge_attrs=dimse_attributes,
        default_attr="elem_type",
        default_value="3",
        default_value_func=dicom_service_default_type,
        ignore_module_level=True,  # <-- Skip module level in path matching
    )

    # --- replace the type with spec from the selected DIMSE and role ---
    align_type_with_dimse_req(merged_model, dimse_req_attributes, dimse_attributes)

    # --- Save the merged model as JSON using JSONSpecStore ---
    merged_model_file = "merged_UPS_IOD.json"
    merged_model_path = os.path.join(config.get_param("cache_dir"), "model", merged_model_file)
    json_store = JSONSpecStore(logger=logger)
    json_store.save(merged_model, merged_model_path)
    print(f"Merged model saved to {merged_model_path}")

    # --- Print or use the merged model ---
    printer = SpecPrinter(merged_model)
    # printer.print_table(colorize=True)

if __name__ == "__main__":
    main()
