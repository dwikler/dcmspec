# API Overview

This section documents the main modules and classes provided by **dcmspec**.

The API enables extraction, parsing, and processing of DICOM specification tables and related data from the DICOM standard and IHE documents for use in Python projects. The modules are organized by functional area and typical workflow, facilitating the discovery of related concepts and effective use of the library.

## Available API Modules

- [Constants Modules](service_attribute_defaults.md): Default values and constants used throughout the library.
- [Core Classes](spec_model.md): Main data models and factories for working with DICOM specifications.
- [Parse Classes](spec_parser.md): Classes for parsing DICOM tables from various formats.
- [Load Classes](doc_handler.md): Classes for loading and handling DICOM documents.
- [Store Classes](spec_store.md): Classes for storing and caching parsed specifications.
- [Print Classes](spec_printer.md): Classes for printing and displaying specification data.
- [Utils Classes](config.md): Utility classes for configuration and DOM manipulation.

## How to Use

You can import and use any API module in your own Python code. For example:

```bash
from dcmspec.spec_model import SpecModel from dcmspec.spec_factory import SpecFactory
```
