# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**dcmspec** is a Python toolkit for downloading, parsing, and modeling DICOM<sup>®</sup> specifications (the DICOM
standard, IHE profiles) into structured, queryable in-memory models. It ships as a library plus a set of sample
CLI scripts and one sample Tkinter UI app that demonstrate the API.

## Commands

Install dependencies (all optional extras, needed for full dev/test coverage):

```bash
poetry install --with dev
poetry run pip install ".[gui,pdf]"
```

Run the test suite:

```bash
poetry run pytest tests
poetry run pytest tests/test_spec_model.py            # single file
poetry run pytest tests/test_spec_model.py::test_name  # single test
poetry run pytest --cov=dcmspec tests                  # with coverage
```

Lint:

```bash
poetry run ruff check src/
```

Run a CLI sample app (each is also registered as a Poetry script, e.g. `poetry run iodattributes ...`):

```bash
poetry run python -m src.dcmspec.apps.cli.iodattributes table_A.3-1 --print-mode tree
```

Build/preview docs:

```bash
mkdocs serve
```

## Architecture

The library is a pipeline of small, swappable stages. Almost every feature is implemented by composing these
stages rather than by adding special cases to one of them:

1. **`DocHandler`** (`doc_handler.py`) — downloads/caches the raw specification document and parses it into an
   in-memory representation. Format-specific subclasses: `XHTMLDocHandler`, `UPSXHTMLDocHandler`, `PDFDocHandler`.
   The base class handles download-with-progress and text/binary streaming; subclasses only need to implement
   `load_document` and, optionally, `clean_text`.
2. **`SpecParser`** (`spec_parser.py`) — turns the handler's parsed document object into a `(metadata, content)`
   pair of `anytree.Node` trees. Subclasses: `DOMTableSpecParser` (XHTML/DOM tables, including `<include>`
   resolution and row/colspan handling — the largest and most complex module in the codebase),
   `CSVTableSpecParser`.
3. **`SpecModel`** (`spec_model.py`) — wraps the `(metadata, content)` node trees and provides the query/manipulation
   API (traversal, filtering, `exclude_titles`, etc.). `ServiceAttributeModel` is a specialized subclass for
   DIMSE service attribute tables.
4. **`SpecStore`** (`spec_store.py`) — caches/loads a built `SpecModel` to/from disk. `JSONSpecStore` is the only
   implementation.
5. **`SpecFactory`** (`spec_factory.py`) — orchestrates steps 1–4: given a URL and table id, it downloads (or uses
   the cache), parses, builds the model, and caches it. This is the main entry point for most consumers
   (`factory.create_model(...)`). It also exposes `load_document`/`build_model` separately for callers that need
   to build a model from a document they already have (e.g. `IODSpecBuilder`).

On top of that pipeline:

- **`IODSpecBuilder`** (`iod_spec_builder.py`) combines an IOD Modules model with per-module Attribute models
  (each built via its own `SpecFactory`) into one expanded model. It supports two modes: legacy "expanded" mode
  (module content is copied under each IOD node) and a reference mode backed by **`ModuleRegistry`**
  (`module_registry.py`), which shares module models by table id across multiple IODs instead of duplicating them.
- **`SpecMerger`** (`spec_merger.py`) merges two `SpecModel`s (e.g. an IOD/module attribute table with a DIMSE
  service attribute table) by matching node path or matching node, used to build combined views like
  UPS IOD+DIMSE attributes.
- **`SpecPrinter`** / **`IODSpecPrinter`** (`spec_printer.py`, `iod_spec_printer.py`) render a `SpecModel` as a
  table, tree, CSV, or XLSX, optionally colorized or written to a file.
- **`Config`** (`config.py`) resolves the cache/config directory via `platformdirs` when no explicit `config_file`
  is given, and is threaded through handlers and factories. Each CLI app independently resolves `config_file`
  before constructing `Config`, preferring the `--config` flag, then the `DCMSPEC_CONFIG` env var, then the
  `platformdirs` default.
- **`Progress`/`ProgressObserver`** (`progress.py`) is the observer-pattern progress-reporting mechanism used
  across downloading, parsing, and saving. Code paths guarded by `# BEGIN/END LEGACY SUPPORT` comments exist to
  keep the older integer `progress_callback` API working during its deprecation — preserve that pattern rather
  than removing it ad hoc.

`src/dcmspec/apps/cli/*.py` are thin, standalone example scripts (each with a `main()` and a Poetry console
script entry in `pyproject.toml`) showing how to wire factories/builders/printers together for a specific DICOM
table family. `src/dcmspec/apps/ui/iod_explorer/` is the sample Tkinter UI app. These apps are developer examples,
not production-grade — don't over-engineer changes to them.

## Testing conventions

- Tests live in the top-level `tests/` directory (flat, one `test_*.py` per source module), **not** under
  `src/dcmspec/tests/` — despite what `pyproject.toml`'s packaging `exclude` and `CONTRIBUTING.md` say.
- `tests/conftest.py` provides an autouse fixture that redirects `platformdirs` cache/config dirs into a per-test
  tmp path, plus shared `SpecModel`/merge fixtures and a `DummyResponse` for mocking `requests`.
- Network access is not used in tests; HTTP is mocked via `DummyResponse`/monkeypatching `requests`.

## Branching and releases

See [RELEASE.md](RELEASE.md) for the full workflow; the essentials:

- No direct commits/pushes to `main` or `release/*` — all changes go through PRs from `feat/`, `fix/`, `change/`,
  or `hotfix/` branches.
- `feat/`, `fix/`, `change/` branches are created from (and PR'd back into) the target `release/x.y.z` branch.
  `hotfix/` branches are created from (and PR'd back into) `main`, then propagated into active release branches.
- CI (`.github/workflows/test.yml`) runs the pytest suite on pushes/PRs to `main` and `release/*` across
  Python 3.10–3.12 on Ubuntu.

## Changelog and roadmap

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/) style:

- Each version is a `## [x.y.z] - YYYY-MM-DD` heading; the in-progress version uses `## [x.y.z] - unreleased`
  until it's released.
- Entries are grouped under `### Added`, `### Changed`, `### Fixed` subsections (only the subsections that apply
  for that version).
- Each entry is a bullet, written user-facing (what changed and why it matters), not a restatement of the
  commit/diff. Entries fixing a reported bug link the GitHub issue, e.g.
  `` ([#85](https://github.com/dwikler/dcmspec/issues/85)) ``.
- Update `CHANGELOG.md` as part of the PR that makes the change, under the current unreleased version section,
  rather than reconstructing it at release time.

Project roadmap is tracked via GitHub milestones on the repo, not in `CHANGELOG.md` or a separate roadmap doc.

## Packaging and PyPI distribution

The package is published to PyPI as [`dcmspec`](https://pypi.org/project/dcmspec/), built with Poetry
(`poetry-core` backend, see `[build-system]`/`[tool.poetry]` in `pyproject.toml`). Core install is
`pip install dcmspec`; `pdf` and `gui` are optional extras (`pip install "dcmspec[pdf,gui]"`) — keep
`[project.dependencies]` vs `[project.optional-dependencies]` in `pyproject.toml` in sync with what
`src/dcmspec/pdf_doc_handler.py` and the Tkinter UI app actually import, since those extras exist specifically to
keep heavy/optional deps (pdfplumber, camelot, opencv, tkhtmlview) out of the core install.

The full local-build/TestPyPI/PyPI publish procedure (including `poetry build`, `poetry publish --build`, and
TestPyPI token setup for maintainers) is documented in [RELEASE.md](RELEASE.md#how-to-test-the-distribution-before-publishing) —
follow it rather than improvising `poetry publish` invocations, since version bumps and CHANGELOG updates must
happen in lockstep with the release branch workflow above.
