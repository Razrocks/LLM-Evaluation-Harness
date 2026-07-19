"""Load eval cases from JSONL.

One JSON object per line. Malformed JSON and schema-invalid cases raise ``CaseLoadError`` with
the exact file and line, so a broken case is a loud, located failure — never a silently
dropped record.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from ai_eval.domain import EvalCase


class CaseLoadError(Exception):
    """A case file could not be parsed or a line failed schema validation."""


def _parse_case(data: object, where: str) -> EvalCase:
    try:
        return EvalCase.model_validate(data)
    except ValidationError as exc:
        raise CaseLoadError(f"{where}: schema-invalid case: {exc}") from exc


def load_cases_jsonl(path: Path) -> list[EvalCase]:
    """Parse every non-blank line of ``path`` into an :class:`EvalCase`."""
    cases: list[EvalCase] = []
    text = path.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CaseLoadError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        cases.append(_parse_case(data, f"{path}:{lineno}"))
    return cases


def load_cases_dir(path: Path) -> list[EvalCase]:
    """Load every ``*.json`` case file in a directory (reviewable, one case per file).

    Cases are returned sorted by ``(case_id, case_version)`` for deterministic ordering.
    """
    files = sorted(path.glob("*.json"))
    cases: list[EvalCase] = []
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CaseLoadError(f"{file}: invalid JSON: {exc}") from exc
        cases.append(_parse_case(data, str(file)))
    return sorted(cases, key=lambda c: (c.case_id, c.case_version))


def dump_cases_jsonl(cases: list[EvalCase], path: Path) -> None:
    """Write cases to JSONL in canonical, stable form (one compact object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(case.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        for case in cases
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
