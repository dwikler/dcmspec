"""CLI for extracting, merging, caching, and printing DICOM UPS IOD attributes from Part 3 and Part 4.

Features:
- Download and parse DICOM UPS IOD (Unified Procedure Step Information Object Definition) from Part 3.
- Merge with UPS DIMSE service requirements and role from Part 4.
- Cache the merged model as a JSON file for future runs and as a structured representation of the standard.
- Print the resulting merged attributes as a table or tree.
- Supports caching, configuration files, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.apps.cli.upsioddimseattributes [options]

For more details, use the --help option.
"""

import argparse
import logging
import os
import re

from anytree import PreOrderIter
from dcmspec.config import Config
from dcmspec.dom_table_spec_parser import DOMTableSpecParser
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_merger import SpecMerger
from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler
from dcmspec.service_attribute_defaults import UPS_DIMSE_MAPPING, UPS_COLUMNS_MAPPING, UPS_NAME_ATTR
from dcmspec.spec_printer import SpecPrinter
from dcmspec.json_spec_store import JSONSpecStore


def dicom_service_default_type(node, merged_model, service_model, default_attr, default_value):
    """Determine the default type value for a node based on its parent context in the service model.

    See PS3.3 Section 5.5 Types and Conditions in Normalized IODs

    When a Normalized IOD in PS3.3 invokes Modules (e.g., the SOP Common Module) or Attribute Macros that are specified
    with Data Element Types, those specified Data Element Types and Conditions do not apply.
    Rather, the Data Element Types and Conditions have to be specified for each Attribute for both SCU and SCP in the
    appropriate Service definition in PS3.4.

    - If the node is a direct child of a module node, and the module has a "catch-all" row in the service model
      (e.g., "All other Attributes of ..."), use the value of default_attr from that row as the default.
    - If no such parent context is found, use the provided default_value.

    Args:
        node: The node for which to determine the default type.
        merged_model: The merged model (not used here, but provided for interface compatibility).
        service_model: The DICOM service attribute model to search for catch-all rows.
        default_attr: The attribute to use as the default (e.g., "elem_type").
        default_value: The fallback value if no catch-all row is found.

    Returns:
        The default value for the type attribute, either from a catch-all row or the provided default.

    """
    # Only apply the catch-all if the node is a direct child of a module node (i.e., grandparent is "content")
    parent = node.parent
    if parent is not None and parent.parent is not None and parent.parent.name == "content":
        # Use the module attribute of the direct parent module node, fallback to name
        module_name = getattr(parent, "module", parent.name)
        # Search for a "catch-all" row in the service model for this module
        pattern = re.compile(
            rf"All (other )?Attributes of( the)? {re.escape(module_name)}( Module)?$"
        )
        for node in service_model.content.descendants:
            node_name = getattr(node, "elem_name", None)
            if node_name and pattern.match(node_name):
            # Found a catch-all row: use its value for default_attr
                val = getattr(node, default_attr, default_value)
                logging.getLogger("modattributes").debug(
                    f"Set default {default_attr} for node '{getattr(node, 'name', None)}' "
                    f"(direct child of module '{module_name}') to '{val}'"
                )
                return val
    
    # No catch-all row found or not a direct child of a module: use the provided default_value
    logging.getLogger("modattributes").debug(
        f"Set default {default_attr} for node '{getattr(node, 'name', None)}' "
        f"(no direct module parent match) to '{default_value}'"
    )
    return default_value


def align_type_with_dimse_req(model, dimse_req_attributes, dimse_attributes):
    """Aligns the "Type" (elem_type) attribute in a DICOM model with the selected DIMSE service/role requirements.

    This function ensures that the correct type attribute is present for each node in the model,
    according to the selected DIMSE service (e.g., N-CREATE, N-SET) and role (e.g., SCU, SCP).
    It removes or moves the "elem_type" attribute as appropriate, so that only the relevant
    DIMSE-specific attribute (e.g., "dimse_ncreate", "dimse_nset") is present.

    The function performs the following steps:
    1. Removes the "Type" column from the model's metadata if present.
    2. For each node in the model:
        - If the node is not a DICOM attribute (i.e., not an element with both elem_name and elem_tag),
          remove the "elem_type" attribute.
        - If the node already has the required DIMSE attribute (e.g., "dimse_ncreate"), remove "elem_type"
          (DIMSE takes precedence).
        - If the node has "elem_type" but not the required DIMSE attribute, move the value from "elem_type"
          to the DIMSE attribute (or to "dimse_all" if no specific DIMSE attribute is required).
    3. Logs debug information for the first 20 processed nodes.

    Args:
        model: The SpecModel to align.
        dimse_req_attributes: List of required DIMSE attribute names for the selected service/role
            (e.g., ["dimse_ncreate"]).
        dimse_attributes: List of all DIMSE attribute names for the selected service/role.

    Returns:
        None. The model is modified in place.

    """
    if not dimse_req_attributes:
        dimse_req_attr = dimse_attributes[0]  # Handle ALL_DIMSE case
    else:
        dimse_req_attr = dimse_req_attributes[0]  # Handle C-FIND case

    # Remove "Type" column from metadata if present
    if hasattr(model.metadata, "header") and "Type" in model.metadata.header:
        # Remove from header
        idx = model.metadata.header.index("Type")
        model.metadata.header.pop(idx)
        # Remove from column_to_attr
        if hasattr(model.metadata, "column_to_attr"):
            # Find the key for "elem_type"
            keys_to_remove = [k for k, v in model.metadata.column_to_attr.items() if v == "elem_type"]
            for k in keys_to_remove:
                model.metadata.column_to_attr.pop(k)

    for node in PreOrderIter(model.content):
        # Remove elem_type from all non DICOM Attribute nodes (e.g., module nodes)
        if hasattr(node, "elem_type") and not (hasattr(node, "elem_name") and hasattr(node, "elem_tag")):
            delattr(node, "elem_type")
        # If the node already has the DIMSE-required attribute, remove elem_type (DIMSE takes precedence)
        elif hasattr(node, dimse_req_attr):
            if hasattr(node, "elem_type"):
                delattr(node, "elem_type")
        # If the node has elem_type but not the DIMSE-required attribute, move elem_type to the DIMSE attribute
        elif hasattr(node, "elem_type"):
            if dimse_req_attributes:
                setattr(node, dimse_req_attr, getattr(node, "elem_type"))
            else:
                # If no specific DIMSE attribute, set to 'dimse_all'
                setattr(node, "dimse_all", getattr(node, "elem_type"))
            delattr(node, "elem_type")


def main():
    """CLI for parsing, merging, caching, and printing DICOM UPS IOD attributes aligned with DIMSE service requirements.

    This CLI downloads, merges, caches, and prints the attributes for a DICOM UPS (Unified Procedure Step) IOD
    (Information Object Definition) from Part 3, aligned with the requirements of a selected DIMSE service and role
    from Part 4.

    The tool parses the IOD table and all referenced module attribute tables, then merges in the UPS DIMSE service
    requirements (e.g., N-CREATE, N-SET, N-GET, C-FIND, FINAL) and role (SCU or SCP) from Part 4. The output can be
    printed as a table or tree.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the merged IOD and DIMSE service attributes, which can be used for further
    processing or integration in other tools. As a secondary benefit, the cache file is also used to speed up
    subsequent runs of the CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.apps.cli.upsioddimseattributes [options]

    Options:
        --config (str): Path to the configuration file.
        --dimse (str): DIMSE service to use (e.g., ALL_DIMSE, N-CREATE, N-SET, N-GET, C-FIND, FINAL).
        --role (str): DIMSE role to use (SCU or SCP).
        --print-mode (str): Print as 'table' (default), 'tree', or 'none' to skip printing.
        -v, --verbose: Enable verbose (info-level) logging to the console.
        -d, --debug: Enable debug logging to the console (overrides --verbose).

    Example:
        poetry run python -m src.dcmspec.apps.cli.upsioddimseattributes --dimse N-CREATE --role SCU --print-mode tree

    """    
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument("--dimse", default="ALL_DIMSE", help="DIMSE service to use (e.g. N-CREATE, N-SET, N-GET, etc.)")
    parser.add_argument("--role", help="DIMSE role to use (e.g. SCU, SCP)")
    parser.add_argument(
        "--print-mode", 
        choices=["table", "tree", "none"],
        default="table",
        help="Print as 'table' (default), 'tree', or 'none' to skip printing"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging to the console (overrides --verbose)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (info-level) logging to the console"
    )
    args = parser.parse_args()

    # Set up logger
    logger = logging.getLogger("modattributes")
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    if args.debug:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)

    # Determine config file location
    config_file = args.config or os.getenv("DCMSPEC_CONFIG", None)
    config = Config(app_name="upsioddimse", config_file=config_file)

    logger.debug(f"Config file: {config_file}")
    logger.debug(f"Cache dir: {config.get_param('cache_dir')}")

    # --- Build the IOD Spec Model (model 1) ---
    iod_url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
    iod_cache_file = "Part3.xhtml"
    iod_table_id = "table_B.26.2-1"
    iod_model_file = "Part3_table_B.26.2-1_expanded.json"

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
    iod_model, _ = builder.build_from_url(
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
        match_by="attribute",
        attribute_name="elem_tag",
        merge_attrs=dimse_attributes,
        default_attr="elem_type",
        default_value="3",
        default_value_func=dicom_service_default_type,
        ignore_module_level=True,
        json_file_name=None  # do not cache as more processing is necessary
    )

    # --- replace the type with spec from the selected DIMSE and role ---
    align_type_with_dimse_req(merged_model, dimse_req_attributes, dimse_attributes)

    # --- Store the aligned model to JSON with _aligned suffix ---
    
    # Build filename for the cached merged model
    dimse_part = args.dimse.replace("-", "").replace(" ", "").upper() if args.dimse else "ALLDIMSE"
    role_part = args.role.upper() if args.role else "ALLROLES"
    merged_model_filename = f"UPSIOD_{dimse_part}_{role_part}.json"

    json_store = JSONSpecStore(logger=logger)
    merged_model_path = os.path.join(config.get_param("cache_dir"), "model", merged_model_filename)
    json_store.save(merged_model, merged_model_path)
    logger.info(f"Aligned model saved to {merged_model_path}")

    # --- Print or use the merged model ---
    printer = SpecPrinter(merged_model)
    if args.print_mode == "tree":
        printer.print_tree(colorize=True)
    elif args.print_mode == "table":
        printer.print_table(colorize=True)
    # else: do not print anything if print_mode == "none"


if __name__ == "__main__":
    main()
