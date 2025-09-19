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

3. **Activate the virtual environment (choose one):**

- Start a new Poetry shell:
  ```bash
  poetry shell
  ```
- Or, activate in your current shell (Poetry 1.2+):

  ```bash
  poetry env activate
  ```

  Then run commands like:

  ```bash
  pytest
  iod-explorer
  ```

  **Alternatively,** you can use `poetry run` for each command without activating the environment:

  ```bash
  poetry run pytest
  poetry run iod-explorer
  ```

5. **Make your changes**

   - Add or update code in `src/dcmspec/`
   - Add or update documentation in `docs/`
   - Add or update tests in `src/dcmspec/tests/`

6. **Run tests and check code style**:

   ```bash
   pytest
   poetry run ruff check src/
   ```

   > **Note:**  
   > The project's Ruff configuration is defined in `pyproject.toml` and will be used automatically.

7. **Build and check documentation** (if applicable):

   - Build and preview the docs locally:
     ```bash
     mkdocs serve
     ```

8. **Commit and push your changes**:

   ```bash
   git add .
   git commit -m "Describe your change"
   git push origin my-feature-branch
   ```

9. **Open a Pull Request**
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
