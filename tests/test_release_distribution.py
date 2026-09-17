"""Contracts for immutable, independently downloadable fork releases."""
from pathlib import Path

from sllurp.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_release_identity_and_installation_docs_are_immutable():
    assert __version__ == "3.1.0"
    assert "## 3.1.0 — 2026-09-17" in read("CHANGELOG.md")
    assert "@v3.1.0" in read("README.rst")
    assert "releases/tag/v3.1.0" in read("README.rst")
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
        "LICENSE.txt",
        "NOTICE.md",
        "CHANGELOG.md",
        "RELEASING.md",
        "RELEASE_NOTES.md",
    ):
        assert f"include {expected}" in manifest


def test_pypi_ownership_boundary_remains_explicit():
    release_notes = read("RELEASE_NOTES.md")
    releasing = read("RELEASING.md")
    assert "PyPI belongs to the upstream project" in release_notes
    assert "Do not configure automatic PyPI publishing" in releasing
