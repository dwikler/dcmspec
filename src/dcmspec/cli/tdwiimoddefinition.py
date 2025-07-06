"""CLI for extracting and printing the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement.

Features:
- Download and parse the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement (PDF).
- Extract and print the module definition as a table and a tree.
- Cache the resulting model as a JSON file for future runs and as a structured representation of the table.
- Supports configuration, caching, and command-line options for flexible workflows.

Usage:
    poetry run python -m src.dcmspec.cli.tdwiimoddefinition [options]

For more details, use the --help option.
"""

import argparse
import logging

from dcmspec.pdf_doc_handler import PDFDocHandler
from dcmspec.csv_table_spec_parser import CSVTableSpecParser
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter

def main():
    """CLI for extracting and printing the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement.

    This CLI downloads, parses, and prints the TDW-II UPS Scheduled Info Base table from the IHE-RO Supplement (PDF).
    The tool extracts the relevant table(s) from the PDF, parses the module definition, and outputs the result as a
    table and a tree.

    The resulting model is cached as a JSON file. The primary purpose of this cache file is to provide a structured,
    machine-readable representation of the module definition, which can be used for further processing or integration
    in other tools. As a secondary benefit, the cache file is also used to speed up subsequent runs of the CLI scripts.

    Usage:
        poetry run python -m src.dcmspec.cli.tdwiimoddefinition [options]

    Options:
        -d, --debug: Enable debug logging.
        -v, --verbose: Enable verbose output.

    Example:
        poetry run python -m src.dcmspec.cli.tdwiimoddefinition

    """
    parser = argparse.ArgumentParser(description="Extract and print TDW-II UPS Scheduled Info Base table.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Set up logger
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("modattributes")

    
    # Set up module definition configuration
    pdf_file = "IHE_RO_Suppl_TDW_II.pdf"
    url = "https://www.ihe.net/uploadedFiles/Documents/Radiation_Oncology/IHE_RO_Suppl_TDW_II.pdf"
    page_numbers = [57, 58]
    table_indices = [(57, 1), (58, 0)]  # Table 1 from page 57, table 0 from page 58
    table_id = "tdwii_ups_scheduled_info_base"
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"}

    # Create the module definition model
    factory = SpecFactory(
        input_handler=PDFDocHandler(logger=logger),
        table_parser=CSVTableSpecParser(logger=logger),
        column_to_attr=column_to_attr,
        name_attr="elem_name",
        logger=logger
    )

    handler_kwargs = {
        "page_numbers": page_numbers,
        "table_indices": table_indices,
        "table_id": table_id,
    }

    model = factory.create_model(
        url=url,
        cache_file_name=pdf_file,
        table_id=table_id,
        force_parse=False,
        json_file_name=f"{table_id}.json",
        handler_kwargs=handler_kwargs,
    )

    # Output the module definition model
    printer = SpecPrinter(model, logger=logger)
    print(f"\nTable for table_id {table_id}:")
    printer.print_table(colorize=True)
    print(f"\nTree for table_id {table_id}:")
    printer.print_tree(attr_names=["elem_name", "elem_tag"], colorize=True)

if __name__ == "__main__":
    main()