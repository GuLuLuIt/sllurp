"""Contracts for immutable, independently downloadable fork releases."""
from pathlib import Path

from sllurp.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_release_identity_and_installation_docs_are_immutable():
    assert __version__ == "3.1.2"
    assert "## 3.1.2 — 2026-09-17" in read("CHANGELOG.md")
    assert "@v3.1.2" in read("README.rst")
    assert "releases/tag/v3.1.2" in read("README.rst")
    for path in (
        "README.rst",
        "QUICKSTART.md",
        "USER_GUIDE.md",
        "docs/index.rst",
        "examples/README.md",
        "RELEASE_NOTES.md",
        "RELEASING.md",
    ):
        assert "3.1.2" in read(path)

    for path in ("README.rst", "QUICKSTART.md", "docs/index.rst", "examples/README.md"):
        assert "@main" not in read(path)


def test_release_workflow_publishes_both_distributions_with_integrity_evidence():
    workflow = read(".github/workflows/release-build.yml")
    for expected in (
        "python -m build",
        "python -m twine check dist/*",
        "sha256sum sllurp-*.whl sllurp-*.tar.gz",
        "actions/attest-build-provenance@v3",
        "gh release create",
        "dist/sllurp-*.whl",
        "dist/sllurp-*.tar.gz",
        "dist/SHA256SUMS.txt",
        "--verify-tag",
        "--notes-file RELEASE_NOTES.md",
    ):
        assert expected in workflow


def test_source_distribution_contains_release_and_legal_documents():
    manifest = read("MANIFEST.in")
    for expected in (
        "README.rst",
        "QUICKSTART.md",
        "USER_GUIDE.md",
        "DEVELOPER_GUIDE.md",
        "LICENSE.txt",
        "NOTICE.md",
        "CHANGELOG.md",
        "RELEASING.md",
        "RELEASE_NOTES.md",
    ):
        assert f"include {expected}" in manifest


def test_user_and_developer_documentation_are_discoverable():
    readme = read("README.rst")
    index = read("docs/index.rst")
    user_guide = read("USER_GUIDE.md")
    developer_guide = read("DEVELOPER_GUIDE.md")

    for expected in ("USER_GUIDE.md", "DEVELOPER_GUIDE.md"):
        assert expected in readme
        assert f"../{expected}" in index

    for heading in (
        "## Command-line workflows",
        "## Python client lifecycle",
        "## Production checklist",
        "## Troubleshooting by symptom",
    ):
        assert heading in user_guide

    for heading in (
        "## Repository map",
        "## Runtime architecture",
        "## Configuration model",
        "## Test strategy",
        "## Documentation contract",
    ):
        assert heading in developer_guide


def test_pypi_ownership_boundary_remains_explicit():
    release_notes = read("RELEASE_NOTES.md")
    releasing = read("RELEASING.md")
    assert "published on PyPI is not this GuLuLuIT build" in release_notes
    assert "Do not configure automatic PyPI publishing" in releasing


def test_project_owned_files_do_not_reference_obsolete_repository_coordinates():
    forbidden = (
        "sllurp" + "/sllurp",
        "github.com/" + "sllurp" + "/sllurp",
    )
    ignored_parts = {
        ".git",
        ".hypothesis",
        ".pytest_cache",
        "__pycache__",
        "build",
        "dist",
        "sllurp.egg-info",
    }
    violations = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz", ".whl"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if any(value in text for value in forbidden):
            violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []
