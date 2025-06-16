import os
import argparse
import logging
from dcmspec.config import Config

from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_merger import SpecMerger
from dcmspec.spec_printer import SpecPrinter


def create_module_model(config, table_id, force_parse, force_download, include_depth, logger=None):
    url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
    cache_file_name = "Part3.xhtml"
    model_file_name = f"Part3_{table_id}.json"
    factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}, 
        name_attr="elem_name",
        config=config,
        logger=logger,
    )
    if logger:
        logger.debug(f"Creating module model: cache_file_name={cache_file_name}, model_file_name={model_file_name}")
    return factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        json_file_name=model_file_name,
        table_id=table_id,
        force_parse=force_parse,
        force_download=force_download,
        include_depth=include_depth,
    )

def create_part6_model(config, logger=None):
    url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html"
    cache_file_name = "DataElements.xhtml"
    json_cache_path = "DataElements.json"
    table_id = "table_6-1"
    factory = SpecFactory(
        column_to_attr={
            0: "elem_tag",
            1: "elem_name",
            2: "elem_keyword",
            3: "elem_vr",
            4: "elem_vm",
            5: "elem_status"
            }, 
        config=config,
        logger=logger,
    )
    logger.debug(f"Creating part6 model: cache_file_name={cache_file_name}, json_cache_path={json_cache_path}")
    return factory.create_model(
        url=url,
        cache_file_name=cache_file_name,
        table_id=table_id,
        force_download=False,
        json_file_name=json_cache_path,
    )

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("table", help="Table ID")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument(
        "--include-depth",
        type=int,
        default=None,
        help="Depth to which included tables should be parsed (default: unlimited)"
    )
    parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Force reparsing of the DOM and regeneration of the JSON model, even if the JSON cache exists."
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help=(
            "Force download of the input file and regeneration of the model, even if cached. "
            "Implies --force-parse (the file will also be re-parsed)."
        )
    )
    parser.add_argument(
        "--print-mode", 
        choices=["table", "tree", "none"],
        default="table",
        help="Print as 'table' (default), 'tree', or 'none' to skip printing"
    )
    parser.add_argument(
        "--add-part6",
        nargs="+",
        choices=["VR", "VM", "Keyword", "Status"],  
        help="Specification to merge from Part 6 (e.g. --add-part6 VR VM)"
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update of the specifications merged from part 6, even if cached"
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
    config = Config(app_name="modattributes", config_file=config_file)

    logger.debug(f"Config file: {config_file}")
    logger.debug(f"Cache dir: {config.get_param('cache_dir')}")
    logger.debug(f"Table ID: {args.table}")

    # Create the module model
    module_model = create_module_model(
        config=config,
        table_id=args.table,
        force_parse=args.force_parse,
        force_download=args.force_download,
        include_depth=args.include_depth,
        logger=logger,
    )

    # Optionally enrich with Part 6
    part6_attr_map = {
        "VR": "elem_vr",
        "VM": "elem_vm",
        "Keyword": "elem_keyword",
        "Status": "elem_status",
    }
    merge_attrs = [part6_attr_map[x] for x in (args.add_part6 or [])]

    if merge_attrs:
        model_file_name = f"Part3_{args.table}_enriched.json"
        part6_model = create_part6_model(config, logger=logger)
        logger.debug("Merging module model with part6 model.")
        merger = SpecMerger(config=config, logger=logger)
        model = merger.merge_node(
            module_model,
            part6_model,
            match_by= "attribute",
            attribute_name="elem_tag",
            merge_attrs=merge_attrs,
            json_file_name=model_file_name,
            force_update=args.force_update or args.force_download or args.force_parse,
        )
    else:
        model = module_model

    logger.debug("Model ready for printing/output")
    printer = SpecPrinter(model)
    if args.print_mode == "tree":
        printer.print_tree(colorize=True)
    elif args.print_mode == "table":
        printer.print_table(colorize=True)
    # else: do not print anything if print_mode == "none"

if __name__ == "__main__":
    main()