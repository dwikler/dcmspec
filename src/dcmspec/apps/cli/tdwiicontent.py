"""CLI for extracting and printing the TDW-II content specifications from the IHE-RO Supplement.

IHE profiles define additional requirements for DICOM Services and Objects.
IOD specifications (which modules are required for each IOD) are defined in section 7.3, "IOD Definitions."
Module specifications (which attributes are defined within each module) are found in section 7.4, "Module Definitions."
In IHE-RO profiles, module specifications are organized into two parts:
- a base definition, which applies to all transactions or content definitions where the module is used
- an extension, which applies only to a particular transaction or content definition.

This CLI tool focuses on the IHE-RO TDW-II workflow profile and extract the content definitions relevant to each 
transaction.

Features:
- Download and parse TDW-II module base and extension definition tables from the IHE-RO Supplement in PDF format.
- Extract and print the module definition as a table and a tree.
- Cache the resulting model as a JSON file for future runs and as a structured representation of the table.
- Supports configuration, caching, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.tdwiimoddefinition [options]

For more details, use the --help option.
"""

import argparse
from copy import deepcopy
import logging

from anytree import Node

from dcmspec.json_spec_store import JSONSpecStore
from dcmspec.pdf_doc_handler import PDFDocHandler
from dcmspec.csv_table_spec_parser import CSVTableSpecParser
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_model import SpecModel
from dcmspec.spec_printer import SpecPrinter

# Configurations for each content definition
CONTENT_DEFINITION_CONFIGS = {
    "ups_scheduled": {
        "page_numbers": [57, 58],
        "table_indices": [(57, 1), (58, 0)],
        "table_id": "tdwii_ups_scheduled_info",
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
    },
    "ups_performed": {
        "page_numbers": [61, 62],
        "table_indices": [(61, 0), (62, 0)],
        "table_id": "tdwii_ups_performed_info",
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
    },
    "ups_progress": {
        "page_numbers": [64],
        "table_indices": [(64,0)],
        "table_header_rowspan": {(64,0): 1},
        "table_id": "tdwii_ups_progress_info",
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
    },
    "ups_relationship": {
        "page_numbers": [60],
        "table_indices": [(60, 1)],
        "table_id": "tdwii_ups_relationship_info",
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
    },
    "ups_query": {
        "page_numbers": [63],
        "table_indices": [(63, 0)],
        "table_header_rowspan": {(63, 0): 2},
        "table_id": "tdwii_ups_query_info",
        "column_to_attr": {
            0: "elem_name",
            1: "elem_tag",
            2: "key_matching_scu",
            3: "key_matching_scp",
            4: "key_return_scu",
            5: "key_return_scp",
        },
    },
    "rt_bdi": {
        "page_numbers": [55, 56, 57],
        "table_indices": [(55, 1), (56, 0), (57, 0)],
        "table_id": "tdwii_bdi_instruction_info",
        "column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
    },
}

def _extract_module_definition(
    pdf_file,
    url,
    page_numbers,
    table_indices,
    table_header_rowspan,
    table_id,
    column_to_attr,
    logger,
    force_parse=False,
):
    """Extract and return the TDW-II module definition model."""
    factory = SpecFactory(
        input_handler=PDFDocHandler(logger=logger, extractor="pdfplumber"),
        table_parser=CSVTableSpecParser(logger=logger),
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        logger=logger
    )

    handler_kwargs = {
        "page_numbers": page_numbers,
        "table_indices": table_indices,
        "table_header_rowspan": table_header_rowspan,
        "table_id": table_id,
    }

    return factory.create_model(
        url=url,
        cache_file_name=pdf_file,
        table_id=table_id,
        force_parse=force_parse,
        json_file_name=f"{table_id}.json",
        handler_kwargs=handler_kwargs,
    )

def _parse_args():
    """Parse and return command-line arguments for the TDW-II CLI."""
    parser = argparse.ArgumentParser(description="Extract and print TDW-II UPS module information tables.")
    parser.add_argument(
        "content_definition",
        choices=[
            "ups_create",
            "ups_performed",
            "ups_progress",
            "ups_query",
            "rt_bdi"
            # Add more content_definition names here as you add configs
        ],
        help=(
            "Select which content definition to extract: "
            "'ups_create', 'ups_query', 'ups_progress', 'ups_performed', 'rt_bdi'"
        )
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()

def _setup_logger(debug=False, verbose=False):
    """Set up and return a logger with the appropriate log level."""
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Suppress PDFMiner debug logs
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    logger = logging.getLogger("tdwiimoddefinition")
    logger.setLevel(log_level)  # <-- This ensures the logger is always at the correct level

    return logger

def _extract_ups_create_model(pdf_file, url, logger):
    """Extract and combine UPS Scheduled and Relationship module definition."""
    base_config = CONTENT_DEFINITION_CONFIGS["ups_scheduled"]
    base_config_part2 = CONTENT_DEFINITION_CONFIGS["ups_relationship"]

    scheduled_model = _extract_module_definition(
        pdf_file=pdf_file,
        url=url,
        page_numbers=base_config["page_numbers"],
        table_indices=base_config["table_indices"],
        table_header_rowspan=base_config.get("table_header_rowspan", None),
        table_id=base_config["table_id"],
        column_to_attr=base_config["column_to_attr"],
        logger=logger,
        force_parse=False,
    )
    relationship_model = _extract_module_definition(
        pdf_file=pdf_file,
        url=url,
        page_numbers=base_config_part2["page_numbers"],
        table_indices=base_config_part2["table_indices"],
        table_header_rowspan=base_config.get("table_header_rowspan", None),
        table_id=base_config_part2["table_id"],
        column_to_attr=base_config_part2["column_to_attr"],
        logger=logger,
        force_parse=False,
    )
    # Combine the two models under a new root node
    combined_root = Node("content")
    # Attach all children of scheduled_model.content
    for child in list(scheduled_model.content.children):
        child.parent = combined_root
    # Attach all children of relationship_model.content
    for child in list(relationship_model.content.children):
        child.parent = combined_root

    # Use metadata from scheduled_model, but set a new table_id for the combined model
    combined_metadata = deepcopy(scheduled_model.metadata)
    combined_metadata.table_id = "tdwii_ups_create_info"
    return SpecModel(
        metadata=combined_metadata,
        content=combined_root,
        logger=logger,
    )

def _apply_hard_coded_extensions(model, content_definition_name):
    """Apply hard-coded extensions to the base model for specific modules."""
    for node in model.content.children:
        elem_name = getattr(node, "elem_name", "").strip()

        if content_definition_name == "ups_create":
            if elem_name == "Scheduled Workitem Code Sequence":
                for child in node.children:
                    child_name = getattr(child, "elem_name", "").strip()
                    if child_name == ">Code Value":
                        child.elem_description = 'shall be equal to "121726"'
                    elif child_name == ">Coding Scheme Designator":
                        child.elem_description = 'shall be equal to "DCM"'
                    elif child_name == ">Code Meaning":
                        child.elem_description = 'shall be equal to "RT Treatment with Internal Verification"'
                continue
            if elem_name == "Input Information Sequence":
                node.elem_description = (
                    "Shall contain at least 2 Referenced DICOM Instances:"
                    "\nRT Plan Storage or RT Ion Plan Storage retrieved from OST."
                    "\nRT Beams Delivery Instruction Storage retrieved from TMS."
                    "\nShall contain more Referenced DICOM Instances if Treatment Delivery Type is equal to "
                    "CONTINUATION:"
                    "\nRT Beams Treatment Record Storage or RT Ion Beams Treatment Record Storage retrieved from OST."
                    "\nMay contain additional items for other reasons, which are out of scope for this profile"
                )
                continue
            if elem_name == "Scheduled Processing Parameters Sequence":
                node.elem_description = (
                    "Shall include 4 Content Items per Template:"
                    '\nEV (121740, DCM, "Treatment Delivery Type"), VT:TEXT (TREAMENT or CONTINUATION).'
                    '\nEV (2018001, 99IHERO2018, "Plan Label"), VT:TEXT (RT Plan Label (300A,0002) value).'
                    '\nEV (2018002, 99IHERO2018, "Current Fraction Number"), VT:NUMERIC '
                    "(Current Fraction Number (3008,0022) value)."
                    '\nEV (2018003, 99IHERO2018, "Number of Fractions Planned"), VT:NUMERIC '
                    "(Number of Fractions Planned (300A,0078) value)."
                )
                continue

        if content_definition_name == "ups_performed":
            if elem_name == ">Performed Workitem Code Sequence":
                for child in node.children:
                    child_name = getattr(child, "elem_name", "").strip()
                    if child_name == ">Code Value":
                        child.elem_description = 'shall be equal to "121726"'
                    elif child_name == ">Coding Scheme Designator":
                        child.elem_description = 'shall be equal to "DCM"'
                    elif child_name == ">Code Meaning":
                        child.elem_description = 'shall be equal to "RT Treatment with Internal Verification"'
                continue
            if elem_name == ">Output Information Sequence":
                node.elem_description = (
                    "Shall contain at least 1 item if any therapeutic treatment was delivered to the patient:"
                    "\nRT Beams Treatment Record Storage (1.2.840.10008.5.1.4.1.1.481.4) or "
                    "RT Ion Beams Treatment Record Storage (1.2.840.10008.5.1.4.1.1.481.9) stored to OST."
                    "\nMay be present otherwise."
                )
                continue

        if content_definition_name == "ups_progress" and elem_name == "Procedure Step Progress Information Sequence":
            # Add missing Procedure Step Progress Parameters Sequence to the model
            Node(
                "procedure_step_progress_parameters_sequence",
                parent=node,
                elem_name=">Procedure Step Progress Parameters Sequence",
                elem_tag="(0074,1007)",
                elem_type="R+*",
                elem_description=(
                    "Shall include 1 Content Item per Template:"
                    '\nEV (2018004, 99IHERO2018, "Referenced Beam Number"), VT:NUM '
                    "(Beam Number (300A,00C0) value of beam in progress)."
                ),
            )
            continue

def main():
    """CLI for extracting and printing the TDW-II Content Definitions from the IHE-RO Supplement.

    This CLI downloads, parses, and prints the TDW-II Content Definitions from the IHE-RO Supplement (PDF).
    The tool extracts the relevant table(s) from the PDF, parses the content definition, and outputs the result as a
    table and a tree.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the content definition, which can be used for further processing or integration
    in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.tdwiicontent <content_definition> [options]

        Where <content_definition> is one of:
        - ups_create: content of scheduled UPS creation (combined UPS Scheduled and Relationship definitions).
        - ups_query: content of C-FIND identifier for UPS Query transaction.
        - ups_progress: content of N-SET dataset for UPS Progress Update transaction.
        - ups_performed: content of N-SET dataset for UPS Final Status Update transaction.
        - rt_bdi: content of RT Beam Delivery Instruction Module.

    Options:
        -d, --debug: Enable debug logging.
        -v, --verbose: Enable verbose output.

    Example:
        poetry run python -m src.dcmspec.apps.cli.tdwiicontent ups_progress --debug

    For more details, use the --help option.

    """
    args = _parse_args()
    logger = _setup_logger(debug=args.debug, verbose=args.verbose)

    logger.info(f"Extracting TDW-II module definition for: {args.content_definition}")
    logger.debug(f"Arguments: {args}")

    # TDW-II Supplement PDF and URL (shared for all module extractions)
    pdf_file = "IHE_RO_Suppl_TDW_II.pdf"
    url = "https://www.ihe.net/uploadedFiles/Documents/Radiation_Oncology/IHE_RO_Suppl_TDW_II.pdf"

    # Special handling for ups_create: combine ups_scheduled and ups_relationship models
    if args.content_definition == "ups_create":
        base_model = _extract_ups_create_model(pdf_file, url, logger)
    else:
        # Select config based on argument
        base_config = CONTENT_DEFINITION_CONFIGS[args.content_definition]

        # Extract base and extension models
        base_model = _extract_module_definition(
            pdf_file=pdf_file,
            url=url,
            page_numbers=base_config["page_numbers"],
            table_indices=base_config["table_indices"],
            table_header_rowspan=base_config.get("table_header_rowspan", None),
            table_id=base_config["table_id"],
            column_to_attr=base_config["column_to_attr"],
            logger=logger,
            force_parse=False,
        )

    # Apply hard-coded extensions for specific modules when the extension specifications is not structured
    # as a single table in the PDF document
    _apply_hard_coded_extensions(base_model, args.content_definition)

    # Cache the final model (base or combined, with hard-coded extensions)
    json_store = JSONSpecStore(logger=logger)
    cache_file_name = f"{getattr(base_model.metadata, 'table_id', 'unknown')}.json"
    cache_path = f"./cache/model/{cache_file_name}"
    json_store.save(base_model, cache_path)
    logger.info(f"Final model saved as JSON to {cache_path}")

    # Print the model
    printer = SpecPrinter(base_model, logger=logger)
    printer.print_table(colorize=True)
    printer.print_tree(attr_names=["elem_name", "elem_tag"], colorize=True)

if __name__ == "__main__":
    main()