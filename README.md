[![tests](https://github.com/dwikler/dcmspec/actions/workflows/test.yml/badge.svg)](https://github.com/dwikler/dcmspec/actions/workflows/test.yml)

# dcmspec

## Overview

**dcmspec** is a versatile **Python toolkit** designed to provide processing of _DICOM specifications_ from the _DICOM standard_ or _IHE profiles_.

Designed as a general-purpose, extensible framework, **dcmspec** enables flexible extraction, parsing, and processing of specification tables.

## Features

- An API to programmatically access, parse, and process DICOM and IHE specification tables.
- Command-Line Interface (CLI) Sample Scripts which extract, parse, and process specific DICOM and IHE specification tables.

## Installation

See the [Installation Guide](https://dwikler.github.io/dcmspec/installation/) for detailed instructions.

## Usage

- For API usage, see the [API documentation](https://dwikler.github.io/dcmspec/api/).
- For CLI usage, see the [CLI Applications Overview](https://dwikler.github.io/dcmspec/cli/).

## Release Notes

See the [Release Notes](https://dwikler.github.io/dcmspec/changelog/) for a summary of changes, improvements, and breaking updates in each version.

## Configuration

See [Configuration & Caching](https://dwikler.github.io/dcmspec/configuration/) for details on configuring cache and other settings.

## Contributing

If you want to contribute to the project, follow these steps:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/dwikler/dcmspec.git
   cd dcmspec
   ```

2. **Install dependencies**:

   ```bash
   poetry install
   ```

3. **Activate the virtual environment**:

   ```bash
   poetry shell
   ```

## Similar Projects

There are a few great related open source projects worth checking out:

- [innolitics/dicom-standard](https://github.com/innolitics/dicom-standard): Tools and data for parsing and working with the DICOM standard in a structured format.
- [pydicom/dicom-validator](https://github.com/pydicom/dicom-validator): A DICOM file validator based on the DICOM standard.

**How dcmspec differs:**

- The above projects focus on parsing specific sections of the DICOM standard to support targeted use cases, such as browsing or validation.
- **dcmspec** is designed with a broader scope. It provides a flexible framework for parsing any DICOM specification table from DICOM standard documents and IHE profiles.
- The object-oriented architecture of **dcmspec** is extensible, making it possible to support additional sources (such as DICOM Conformance Statements) and to define custom structured data models as output.
