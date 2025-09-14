[![tests](https://github.com/dwikler/dcmspec/actions/workflows/test.yml/badge.svg)](https://github.com/dwikler/dcmspec/actions/workflows/test.yml)

# dcmspec

## Overview

**dcmspec** is a versatile **Python toolkit** designed to provide processing of DICOM<sup>®</sup> specifications from the DICOM standard or IHE profiles.

Designed as a general-purpose, extensible framework, **dcmspec** enables flexible extraction, parsing, and processing of DICOM specifications.

## Features

- An API to programmatically access, parse, and process DICOM and IHE specifications.
- Command-Line Interface (CLI) Sample Scripts which extract, parse, and process specific DICOM and IHE specifications.
- User Interface (UI) sample application for interactive exploration of DICOM IODs.

> **Note:** CLI and UI sample applications are provided as developer examples and are not intended to be full-featured or production-grade applications.

## Installation

See the [Installation Guide](https://dwikler.github.io/dcmspec/installation/) for detailed instructions.

## Usage

- For API usage, see the [API documentation](https://dwikler.github.io/dcmspec/api/).
- For example developer applications usage (CLI and UI), see:
  - [CLI Applications Overview](https://dwikler.github.io/dcmspec/cli/)
  - [UI Application Overview](https://dwikler.github.io/dcmspec/ui/)

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
- **dcmspec** is designed with a broader scope. It provides a flexible framework for parsing any DICOM specification document, including the DICOM Standard itself, DICOM Conformance Statements, and IHE Integration Profiles.
- The object-oriented architecture of **dcmspec** is extensible, making it possible to support additional sources, and to define custom structured data models as output.

---

<sub>
DICOM<sup>®</sup> is the registered trademark of the National Electrical Manufacturers Association for its Standards publications relating to digital communications of medical information.<br>
<br>
National Electrical Manufacturers Association (NEMA), Rosslyn, VA USA.<br>
PS3 / ISO 12052 Digital Imaging and Communications in Medicine (DICOM) Standard.<br>
<a href="http://www.dicomstandard.org">http://www.dicomstandard.org</a>
</sub>
