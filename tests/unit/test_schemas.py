"""M0 schema-lock tests.

Proves every JSON Schema under ``schemas/`` is itself a valid draft 2020-12
schema, and that every example payload validates against its schema (with
cross-schema ``$ref`` resolution through a referencing registry). Offline; no
credentials required.

Examples live in ``schemas/examples/`` named ``<concept>.example.json`` and map
to the versioned schema ``<concept>.vN.json`` (found anywhere under ``schemas/``)
by the concept stem, so ``request_triage_output.example.json`` validates against
``schemas/reference/request_triage_output.v1.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"
EXAMPLES_DIR = SCHEMAS_DIR / "examples"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_files() -> list[Path]:
    """All contract schemas, excluding example payloads."""
    return sorted(p for p in SCHEMAS_DIR.rglob("*.json") if EXAMPLES_DIR not in p.parents)


def _example_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.rglob("*.example.json"))


def _concept(name: str) -> str:
    """Version-agnostic concept stem: 'assertion.v1.json' and
    'assertion.example.json' both reduce to 'assertion'."""
    return name.replace(".example.json", "").replace(".json", "").split(".v")[0]


def _schema_by_concept() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in _schema_files():
        concept = _concept(path.name)
        assert concept not in mapping, f"ambiguous schema concept '{concept}' ({path.name})"
        mapping[concept] = path
    return mapping


def _registry() -> Registry:
    """A referencing registry of every schema, keyed by ``$id`` for ref resolution."""
    resources = [(_load(p)["$id"], Resource.from_contents(_load(p))) for p in _schema_files()]
    return Registry().with_resources(resources)


@pytest.mark.parametrize("schema_path", _schema_files(), ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    schema = _load(schema_path)
    assert schema.get("$schema", "").endswith("2020-12/schema"), (
        f"{schema_path.name} missing draft 2020-12 $schema"
    )
    assert "$id" in schema, f"{schema_path.name} missing $id"
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("example_path", _example_files(), ids=lambda p: p.name)
def test_example_validates_against_schema(example_path: Path) -> None:
    concept = _concept(example_path.name)
    schema_map = _schema_by_concept()
    assert concept in schema_map, f"no schema for example concept '{concept}' ({example_path.name})"
    validator = Draft202012Validator(_load(schema_map[concept]), registry=_registry())
    errors = sorted(
        validator.iter_errors(_load(example_path)),
        key=lambda e: list(map(str, e.path)),
    )
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_every_schema_has_an_example() -> None:
    schema_concepts = set(_schema_by_concept())
    example_concepts = {_concept(p.name) for p in _example_files()}
    missing = schema_concepts - example_concepts
    assert not missing, f"schemas without example payloads: {sorted(missing)}"
