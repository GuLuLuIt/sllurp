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
        "API_REFERENCE.md",
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
        "API_REFERENCE.md",
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
    api_reference = read("API_REFERENCE.md")

    for expected in ("USER_GUIDE.md", "DEVELOPER_GUIDE.md", "API_REFERENCE.md"):
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

    for heading in (
        "## Minimal inventory client",
        "## `LLRPReaderConfig`",
        "## `LLRPReaderClient`",
        "## Live configuration",
        "## Secure LLRP/TLS",
        "## Reader management APIs",
        "## Exceptions and failure handling",
        "## Compatibility and API boundaries",
    ):
        assert heading in api_reference

    for public_name in (
        "LLRPReaderConfig",
        "LLRPReaderClient",
        "LLRPTLSReaderClient",
        "TagReportDeduplicator",
        "create_reader_manager",
        "parse_sgtin_96",
    ):
        assert public_name in api_reference


def test_repository_support_surfaces_are_complete():
    readme = read("README.rst")
    support = read("SUPPORT.md")
    security = read("SECURITY.md")
    project = read("pyproject.toml")

    for path in (
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/hardware_compatibility.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
    ):
        assert (ROOT / path).is_file()

    assert "issues/new/choose" in readme
    assert "issues/new/choose" in support
    assert "releases/tag/v3.1.2" in security
    assert 'Issues = "https://github.com/GuLuLuIt/sllurp/issues/new/choose"' in project
    assert 'Releases = "https://github.com/GuLuLuIt/sllurp/releases"' in project

    for placeholder in ("READER_USERNAME", "READER_PASSWORD"):
        assert placeholder in readme


def test_release_notes_are_a_cumulative_supported_baseline():
    release_notes = read("RELEASE_NOTES.md")
    changelog = read("CHANGELOG.md")

    for expected in (
        "first complete, supported GuLuLuIT package baseline",
        "## What is included",
        "## Material bug fixes included",
        "## Compatibility and deprecated behavior",
        "### LLRP inventory and tag operations",
        "### Secure transport",
        "### Reporting, deduplication, and RF observations",
        "### Live configuration and reliability",
        "### Reader management",
        "### Protocol and decoder correctness",
        "### Runtime and state correctness",
        "### CLI, logging, data, and security correctness",
    ):
        assert expected in release_notes

    for expected in (
        "### Core LLRP and application features",
        "### Secure transport and reader compatibility",
        "### Reporting, deduplication, and telemetry",
        "### Runtime configuration and request handling",
        "### Reader management",
        "### Protocol and wire-format fixes",
        "### State-machine, concurrency, and lifecycle fixes",
        "### CLI, logging, data, and validation fixes",
        "### Compatibility and deprecation status",
    ):
        assert expected in changelog


def test_release_notes_document_retained_compatibility_interfaces():
    release_notes = read("RELEASE_NOTES.md")
    for expected in (
        "report_every_n_tags",
        "report_timeout_ms",
        "ro_report_every_n_tags",
        "Channelist",
        "ChannelList",
        "SecureLLRPReaderClient",
        "LLRPTLSReaderClient",
    ):
        assert expected in release_notes


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
