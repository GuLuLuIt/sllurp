import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
RST_INLINE_LINK_RE = re.compile(r"`[^`]*?<([^>]+)>`_")
RST_TARGET_RE = re.compile(r"^\s*:target:\s+(\S+)\s*$", re.MULTILINE)
EXTERNAL_SCHEMES = {"http", "https", "mailto", "ftp", "tel", "data"}
IGNORED_PARTS = {
    ".artifacts-api",
    ".git",
    ".hypothesis",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "sllurp.egg-info",
    "site-packages",
    "venv",
}


def _is_generated_or_environment_path(path):
    parts = path.relative_to(ROOT).parts
    return any(
        part in IGNORED_PARTS
        or part == ".venv"
        or part.endswith(".egg-info")
        or part.startswith((".artifacts-", ".pytest-", ".wheel-smoke-"))
        for part in parts
    )


def _documentation_files():
    files = set(ROOT.rglob("*.md")) | set(ROOT.rglob("*.rst"))
    return sorted(
        path
        for path in files
        if not _is_generated_or_environment_path(path)
    )


def _link_targets(text):
    yield from MARKDOWN_LINK_RE.findall(text)
    yield from RST_INLINE_LINK_RE.findall(text)
    yield from RST_TARGET_RE.findall(text)


def _relative_target(target):
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    # Markdown may append an optional link title after the target.
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(" ", 1)[0]

    parsed = urlsplit(target)
    if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
        return None
    if not parsed.path or parsed.path.startswith("/"):
        return None
    return unquote(parsed.path)


@pytest.mark.parametrize(
    "source",
    _documentation_files(),
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_internal_documentation_links_resolve(source):
    broken = []
    for target in _link_targets(source.read_text(encoding="utf-8")):
        relative = _relative_target(target)
        if relative is None:
            continue

        destination = (source.parent / relative).resolve()
        try:
            destination.relative_to(ROOT.resolve())
        except ValueError:
            broken.append(f"{target} (escapes repository)")
            continue

        if not destination.exists():
            broken.append(target)

    assert not broken, f"Broken internal links in {source.relative_to(ROOT)}: {broken}"

