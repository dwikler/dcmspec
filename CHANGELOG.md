# Release Notes

These release notes summarize key changes, improvements, and breaking updates for each version of **dcmspec**.

## [0.2.1] - 2025-09-19

### Fixed

- Sanitize node and attribute names to remove "/" in DOMTableSpecParser ([#56](https://github.com/dwikler/dcmspec/issues/56))

### Changed

- Major project restructure: moved CLI and UI apps to new `apps/cli` and `apps/ui` folders
- Improved installation instructions and documentation
- Prepared and published the package to [PyPI](https://pypi.org/project/dcmspec/)

## [0.2.0] - 2025-09-13

### Changed

- **Breaking change:** `IODSpecBuilder.build_from_url` now returns a tuple `(iod_model, module_models)` instead of just the IOD model. All callers must be updated to unpack the tuple.
- Updated CLI and UI applications to support new return value.
- Added registry mode to `IODSpecBuilder` for efficient module model sharing.

## [0.1.0] - 2025-05-25

### Added

- Initial release.
