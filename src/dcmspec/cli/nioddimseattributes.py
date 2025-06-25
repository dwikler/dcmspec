import os
from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_merger import SpecMerger
from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler
from dcmspec.csv_table_spec_parser import CSVTableSpecParser
from dcmspec.pdf_doc_handler import PDFDocHandler
from dcmspec.service_attribute_defaults import UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR
from dcmspec.spec_printer import SpecPrinter

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

def main():
    # --- Build the IOD Spec Model (model 1) ---
    iod_url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
    iod_cache_file = "Part3.xhtml"
    iod_table_id = "table_B.26.2-1"
    iod_model_file = "Part3_table_B.26.2-1_expanded.json"

    config = Config(app_name="dcmspec")

    iod_factory = SpecFactory(
        column_to_attr={0: "module", 1: "ref", 2: "usage"},
        name_attr="module",
        config=config,
    )
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
        parser_kwargs={"skip_columns": [2]},
        config=config,
    )
    builder = IODSpecBuilder(iod_factory=iod_factory, module_factory=module_factory)
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
    ups_table_id = "table_CC.2.5-3"

    ups_factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(config=config),
        table_parser=CSVTableSpecParser(logger=None),
        column_to_attr=UPS_COLUMNS_MAPPING,
        name_attr=UPS_NAME_ATTR,
        config=config
    )
    ups_model = ups_factory.create_model(
        url=ups_url,
        cache_file_name=ups_cache_file,
        table_id=ups_table_id,
        force_download=False,
        model_kwargs={"dimse_mapping": UPS_DIMSE_MAPPING},
    )

    # --- Merge by path with DICOM service default type logic ---
    merger = SpecMerger(config=config)
    merged_model = merger.merge_path_with_default(
        iod_model,
        ups_model,
        default_attr="elem_type",
        default_value="3",
        default_value_func=dicom_service_default_type,
    )

    # --- Print or use the merged model ---
    printer = SpecPrinter(merged_model)
    printer.print_table(colorize=True)

if __name__ == "__main__":
    main()
