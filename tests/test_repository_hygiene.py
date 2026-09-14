from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_repository_artifacts_are_not_reintroduced():
    stale_paths = [
        ROOT / "bin",
        ROOT / "examples" / "caps.dat",
        ROOT / "examples" / "caps.txt",
        ROOT / "examples" / "tornado",
        ROOT / "examples" / "fastapi" / "uv.lock",
        ROOT / "examples" / "fastapi" / "pyproject.toml",
        ROOT / "docs" / "impinj-r1000-hybrid-mode-rospec.xml",
    ]
    assert not [str(path.relative_to(ROOT)) for path in stale_paths if path.exists()]


def test_llrp_standards_are_linked_not_bundled_as_pdfs():
    assert not list((ROOT / "docs").glob("llrp_*-standard-*.pdf"))


def test_fastapi_requirements_do_not_install_upstream_sllurp():
    requirements = (ROOT / "examples" / "fastapi" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    active_lines = [
        line.strip().lower()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not any(line.startswith("sllurp") for line in active_lines)
