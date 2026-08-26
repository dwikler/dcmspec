# Contributing to dcmspec

Thank you for your interest in contributing to **dcmspec**!  
We welcome bug reports, feature requests, documentation improvements, and code contributions.

## How to Contribute

1. **Clone the repository** and create your feature branch:

   ```bash
   git clone https://github.com/dwikler/dcmspec.git
   cd dcmspec
   git checkout -b my-feature-branch
   ```

2. **Install all development dependencies** (including optional features):

   ```bash
   poetry install --with dev
   poetry run pip install ".[gui,pdf]"
   ```

> **Note:** This will install all development, GUI, and PDF dependencies so you can test and work on every feature.
> For details on what each dependency group includes, see the [Dependencies and Optional Features section in the installation guide](https://dwikler.github.io/dcmspec/installation/#dependencies-and-optional-features).

3. **(Optional) Activate the virtual environment:**

   ```bash
   poetry shell
   ```

   Or, for Poetry 1.2+:

   ```bash
   poetry env activate
   ```

   All commands in this guide are shown with the `poetry run` prefix, which works whether or
   not you've activated the environment.

4. **Make your changes**

   - Add or update code in `src/dcmspec/`
   - Add or update documentation in `docs/`
   - Add or update tests in `tests/unit/` (or `tests/integration/`, `tests/e2e/` as appropriate)

5. **Run tests and check code style**:

   ```bash
   poetry run pytest tests/unit tests/integration
   poetry run ruff check src/
   ```

   > **Note:**  
   > The project's Ruff configuration is defined in `pyproject.toml` and will be used automatically.
   >
   > `tests/e2e` is an opt-in canary suite that hits the live DICOM standard site; it's excluded
   > from the command above and not required for a PR. Run it with `poetry run pytest tests/e2e` if you want
   > to check it separately. Add `-s` to see where it downloaded the standard to and where each
   > test wrote its full parsed output (too large to print directly), or `--basetemp=<dir>` to
   > control that location yourself, e.g.
   > `mkdir -p tmp/dcmspec-e2e && poetry run pytest tests/e2e -s --basetemp=tmp/dcmspec-e2e` (`tmp/` is
   > gitignored; `--basetemp` needs it to already exist). Unlike the default location, pytest does
   > not auto-clean a directory you pass via `--basetemp` — it's wiped and recreated on the next
   > run that reuses the same path, but otherwise left in place, so removing it is on you.

6. **Build and check documentation** (if applicable):

   - Build and preview the docs locally:
     ```bash
     mkdocs serve
     ```

7. **Commit and push your changes**:

   ```bash
   git add .
   git commit -m "Describe your change"
   git push origin my-feature-branch
   ```

8. **Open a Pull Request**
   - Go to https://github.com/dwikler/dcmspec and open a PR from your branch.

## Guidelines

- Follow the [PEP8](https://www.python.org/dev/peps/pep-0008/) style guide.
- Write clear commit messages.
- Add or update tests for new features or bug fixes.
- Update documentation as needed.
- For large changes, consider opening an issue or starting a discussion first to discuss your proposal.

## Need Help?

If you have questions or need help, open an [issue](https://github.com/dwikler/dcmspec/issues) or start a discussion.

Thank you for helping make **dcmspec** better!
