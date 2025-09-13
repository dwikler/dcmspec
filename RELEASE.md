# Release Checklist for dcmspec

> **Note:** This checklist is intended for project maintainers and developers.  
> It is not required for users of the dcmspec library.

1. [ ] Update `pyproject.toml` with the new version number.
2. [ ] Add a new section to `docs/changelog.md` for the release:

   - Use the format:

   ```
   ## [x.y.z] - YYYY-MM-DD

   ### Added
   - Support for ... ([#NN](https://github.com/dwikler/dcmspec/issues/NN))

   ### Changed
   - Improved ... ([#NN](https://github.com/dwikler/dcmspec//issues/NN))

   ### Fixed
   - Corrected ... ([#NN](https://github.com/yourrepo/issues/NN))
   ```

   - Use **"Added"** for new features, **"Changed"** for enhancements or improvements, and **"Fixed"** for bug fixes.

3. [ ] Commit the changes:
   ```
   git add [pyproject.toml](VALID_FILE) [docs/changelog.md](VALID_FILE)
   git commit -m "Bump version to x.y.z and update changelog"
   ```
4. [ ] Tag the release:

   For a new feature:

   ```
   git tag -a vX.Y.Z -m "Add support for ... (#NN)"
   ```

   For an enhancement:

   ```
   git tag -a vX.Y.Z -m "Improve ... (#NN)"
   ```

   For a bug fix:

   ```
   git tag -a vX.Y.Z -m "Corrected ... (#NN)"
   ```

5. [ ] Push commits and tags:
   ```
   git push
   git push --tags
   ```
6. [ ] Create a GitHub Release for the new tag:
   - Copy the changelog entry into the release notes.

---

## How to Move the Tag

If you forgot to update a file (like `pyproject.toml` or `changelog.md`) before tagging, you can move the tag to the correct commit after making the necessary changes:

1. Make and commit the missing changes.

2. Delete the old tag locally:

   ```
   git tag -d vX.Y.Z
   ```

3. Re-create the tag on the latest commit:

   ```
    git tag -a vX.Y.Z -m "Your release message"
   ```

4. Force-push the updated tag to GitHub:

   ```
    git push --force origin vX.Y.Z
   ```

**Note:** Only force-push tags if you are sure no one else is relying on the old tag, or coordinate with your team if you are working with others.
