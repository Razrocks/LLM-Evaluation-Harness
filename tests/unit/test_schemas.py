"""M0 schema-lock tests.

Proves every JSON Schema under ``schemas/`` is itself a valid draft 2020-12
schema, and that every example payload validates against its schema (with
cross-schema ``$ref`` resolution through a referencing registry).
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
    return sorted(p for p in SCHEMAS_DIR.rglob("*.json") if EXAMPLES_DIR not in p.parents)


def _registry() -> Registry:
    resources = [(_load(p)["$id"], Resource.from_contents(_load(p))) for p in _schema_files()]
    return Registry().with_resources(resources)


def _stem_before_version(name: str) -> str:
    # "request_triage_output.v1.json" -> "request_triage_output"
    return name.split(".v")[0]


def _schema_by_stem() -> dict[str, Path]:
    return {_stem_before_version(p.name): p for p in _schema_files()}


@pytest.mark.parametrize("schema_path", _schema_files(), ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    schema = _load(schema_path)
    assert schema.get("$schema", "").endswith("2020-12/schema"), f"{schema_path.name} missing draft 2020-12 $schema"
    assert "$id" in schema, f"{schema_path.name} missing $id"
    Draft202012Validator.check_schema(schema)


def _example_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.example.json"))


@pytest.mark.parametrize("example_path", _example_files(), ids=lambda p: p.name)
def test_example_validates_against_schema(example_path: Path) -> None:
    stem = example_path.name.replace(".example.json", "")
    schema_map = _schema_by_stem()
    assert stem in schema_map, f"no schema found for example {example_path.name}"
    schema = _load(schema_map[stem])
    validator = Draft202012Validator(schema, registry=_registry())
    validator.validate(_load(example_path))


def test_every_schema_has_an_example() -> None:
    schema_stems = set(_schema_by_stem())
    example_stems = {p.name.replace(".example.json", "") for p in _example_files()}
    missing = schema_stems - example_stems
    assert not missing, f"schemas without example payloads: {sorted(missing)}"
