"""Strict output parsing — the boundary between raw evidence and scored data.

Two failure modes are kept distinct (ADR 0002): malformed JSON is a *parse* error, valid JSON
that violates the schema is a *schema* error. Nothing is ever silently repaired or coerced; an
invalid output becomes a typed failure carrying its evidence, never a fabricated pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import ValidationError

from ai_eval.domain import FailureCode

from .models import TriageOutput


class ParseStatus(StrEnum):
    PARSED = "parsed"
    EMPTY = "empty"
    PARSE_ERROR = "parse_error"
    SCHEMA_ERROR = "schema_error"


@dataclass
class ParseOutcome:
    """The result of parsing one raw candidate output. Exactly one status; evidence retained."""

    status: ParseStatus
    value: dict[str, Any] | None = None
    model: TriageOutput | None = None
    failure_code: FailureCode | None = None
    message: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status is ParseStatus.PARSED


def parse_triage_output(raw: str | None) -> ParseOutcome:
    """Parse and schema-validate a raw candidate output string. No repair, no coercion."""
    if raw is None or raw.strip() == "":
        return ParseOutcome(
            ParseStatus.EMPTY,
            failure_code=FailureCode.OUTPUT_EMPTY,
            message="target returned empty output",
        )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ParseOutcome(
            ParseStatus.PARSE_ERROR,
            failure_code=FailureCode.OUTPUT_PARSE_ERROR,
            message=f"malformed JSON: {exc}",
        )
    try:
        model = TriageOutput.model_validate(value)
    except ValidationError as exc:
        return ParseOutcome(
            ParseStatus.SCHEMA_ERROR,
            value=value if isinstance(value, dict) else None,
            failure_code=FailureCode.OUTPUT_SCHEMA_INVALID,
            message="output does not conform to request_triage.output.v1",
            errors=[
                {"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]}
                for e in exc.errors()
            ],
        )
    return ParseOutcome(ParseStatus.PARSED, value=value, model=model)
