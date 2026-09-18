"""Contracts for the public API and its protocol documentation."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MODULES = (
    "sllurp/llrp.py",
    "sllurp/llrp_runtime.py",
    "sllurp/llrp_decoder.py",
    "sllurp/llrp_errors.py",
    "sllurp/secure.py",
    "sllurp/dedup.py",
    "sllurp/readers.py",
    "sllurp/reader_management.py",
    "sllurp/zebra_management.py",
    "sllurp/impinj_management.py",
    "sllurp/intermec_management.py",
    "sllurp/util.py",
    "sllurp/log.py",
    "sllurp/epc/gtin.py",
    "sllurp/epc/sgtin_96.py",
)


def _tree(relative: str) -> ast.Module:
    return ast.parse((ROOT / relative).read_text(encoding="utf-8"))


def test_public_classes_functions_methods_and_properties_have_docstrings():
    missing = []
    for relative in PUBLIC_MODULES:
        tree = _tree(relative)
        for node in tree.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                missing.append(f"{relative}:{node.name}")
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if not isinstance(member, ast.FunctionDef):
                        continue
                    if member.name.startswith("_"):
                        continue
                    if not ast.get_docstring(member):
                        missing.append(f"{relative}:{node.name}.{member.name}")

    assert missing == []


def test_every_configuration_field_is_named_in_the_api_reference():
    tree = _tree("sllurp/llrp.py")
    config_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "LLRPReaderConfig"
    )
    init = next(
        node
        for node in config_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    fields = {
        node.attr
        for node in ast.walk(init)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and isinstance(node.ctx, ast.Store)
    }
    reference = (ROOT / "API_REFERENCE.md").read_text(encoding="utf-8")

    assert fields
    assert [field for field in sorted(fields) if f"`{field}`" not in reference] == []


def test_reference_documents_concurrency_wire_and_failure_contracts():
    reference = (ROOT / "API_REFERENCE.md").read_text(encoding="utf-8")
    for required in (
        "## Callback and thread-context contract",
        "## Return values and failure behavior",
        "## Live-transition invariants and rollback",
        "## State-machine invariants",
        "## Timeout and request-correlation rules",
        "## Protocol bit layouts and wire order",
        "## C1G2 operation units",
        "## Protocol section map",
        "(expected response message name, request message ID)",
        "network byte order",
        "https://ref.gs1.org/standards/llrp/1.1.0/",
    ):
        assert required in reference


def test_wire_helpers_cite_the_authoritative_binary_encoding_sections():
    decoder = (ROOT / "sllurp/llrp_decoder.py").read_text(encoding="utf-8")
    for required in (
        "https://ref.gs1.org/standards/llrp/1.1.0/",
        "section 17.1",
        "section 17.2.1",
        "network byte order",
        "Reserved(3), Version(3), Type(10)",
        "Reserved(6), Type(10)",
    ):
        assert required in decoder


def test_exported_protocol_helpers_have_docstrings():
    tree = _tree("sllurp/llrp_proto.py")
    public_callables = {
        "get_message_name_from_type",
        "llrp_data2xml",
        "LLRPROSpec",
        "LLRPMessageDict",
    }
    nodes = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        and node.name in public_callables
    }

    assert set(nodes) == public_callables
    assert [name for name, node in nodes.items() if not ast.get_docstring(node)] == []

