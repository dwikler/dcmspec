# Release Notes

These release notes summarize key changes, improvements, and breaking updates for each version of **dcmspec**.

## [0.2.0] - 2025-09-13

### Changed

- **Breaking change:** `IODSpecBuilder.build_from_url` now returns a tuple `(iod_model, module_models)` instead of just the IOD model. All callers must be updated to unpack the tuple.
- Updated CLI and UI applications to support new return value.
- Added registry mode to `IODSpecBuilder` for efficient module model sharing.

## [0.1.0] - 2025-05-25

### Added

- Initial release.
