import argparse
import logging

from dcmspec.pdf_doc_handler import PDFDocHandler
from dcmspec.csv_table_spec_parser import CSVTableSpecParser
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_printer import SpecPrinter

def main():
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