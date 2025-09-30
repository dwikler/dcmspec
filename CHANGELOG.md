# Release Notes

These release notes summarize key changes, improvements, and breaking updates for each version of **dcmspec**.

## [0.2.3] - 2025-09-29

### Fixed

- Hotfix: Force UTF-8 decoding for DICOM standard XHTML downloads to prevent mojibake when server omits charset ([#85](https://github.com/dwikler/dcmspec/issues/85)).
- Hotfix: Add missing `progress_observer` argument to `CSVTableSpecParser.parse` for interface compatibility and to prevent `TypeError` when used with `SpecFactory` ([#86](https://github.com/dwikler/dcmspec/issues/86)).

## [0.2.2] - 2025-09-25

### Fixed

- Fix CONTRIBUTING.md link in README for PyPI compatibility
- Remove focus border and misleading text cursor in iod-explorer details panel

### Changed

- Update README: add PyPI and Python version badges
- Replace Unicode ▶ with ASCII > in status bar for compatibility
- Improve DICOM Modules usage condition parsing using regex for robustness to missing spaces
- Add PR template to remind contributors to check the target branch and check tests and docs were updated
- Move detailed table parsing logs to DEBUG level for less verbose INFO output

## [0.2.1] - 2025-09-19

### Fixed

- Sanitize node and attribute names to remove "/" in DOMTableSpecParser ([#56](https://github.com/dwikler/dcmspec/issues/56))

### Changed

- Major project restructure: move CLI and UI apps to new `apps/cli` and `apps/ui` folders
- Improve installation instructions and documentation
- Prepare and publish the package to [PyPI](https://pypi.org/project/dcmspec/)

## [0.2.0] - 2025-09-13

### Changed

- **Breaking change:** `IODSpecBuilder.build_from_url` now returns a tuple `(iod_model, module_models)` instead of just the IOD model. All callers must be updated to unpack the tuple
- Update CLI and UI applications to support new return value
- Add registry mode to `IODSpecBuilder` for efficient module model sharing

## [0.1.0] - 2025-05-25

### Added

- Initial release
