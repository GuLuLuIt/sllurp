# Releasing Sllurp

This fork currently installs from GitHub and has not published a GitHub release. Treat publishing as an explicit maintainer action, not an automatic side effect of tagging.

## Release checklist

1. Ensure `main` is green and up to date.
2. Confirm the intended semantic version in `sllurp/version.py`; update it before the release-preparation PR if needed.
3. Move relevant entries from `CHANGELOG.md` `Unreleased` into a dated release section.
4. Run the full local gate:

   ```bash
   python -m pip install -e ".[dev]"
   pytest -W error
   pytest --cov=sllurp --cov-branch --cov-fail-under=65
   python -m compileall -q sllurp tests examples
   ruff check sllurp tests examples --select E9,F63,F7,F82,F401,F841,E722,B006,ISC004,B017
   bandit -r sllurp -q
   codespell
   python -m build
   python -m twine check dist/*
   sllurp --version
   ```

5. Verify the built wheel in a clean virtual environment and confirm `sllurp --version` reports the release version.
6. Create and merge a release-preparation pull request.
7. Tag the exact release commit, for example `v3.1.0`.
8. Let the release-build workflow build and validate the source distribution and wheel.
9. Create a GitHub Release from the tag and attach or reference the validated artifacts.

## PyPI

The package name `sllurp` already exists on PyPI and is associated with the upstream project. Do not configure automatic PyPI publishing from this fork unless the maintainer has explicit rights to publish that package and has intentionally configured GitHub trusted publishing for this repository.

If this fork needs independent distribution without upstream PyPI ownership, use a distinct package/distribution name and document the compatibility implications before publishing.

## Version consistency

A release tag, `sllurp/version.py`, `sllurp --version`, wheel metadata, changelog section, and GitHub Release should all agree on the same version. Do not tag a feature-bearing release while leaving the package version at an inherited upstream value.
