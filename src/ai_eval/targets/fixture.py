"""Deterministic recorded target adapters — the offline, credential-free targets.

Each fixture synthesizes a candidate ``request_triage.output.v1`` payload deterministically from
the case's approved ``expected`` values, then (for the regression variants) mutates exactly one
dimension. This makes the first-checkpoint demo and CI reproducible with no model and no keys:
``recorded_pass`` is a known-good baseline; each regression variant is a known, isolated defect
the scorers (M3) and gate (M4) must catch.

As documented on :class:`TargetAdapter`, reading ``case.expected`` is legitimate *because these
are test doubles*; live provider adapters (M5) read only ``case.input``.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from ai_eval.domain import EvalCase, content_hash

from .base import Attempt, InvocationContext, TargetAdapter, TargetInvocationResult


def _first_evidence(case: EvalCase) -> list[str]:
    for unit in case.source_context:
        return [unit.evidence_id]
    return ["message#span-1"]


def build_correct_output(case: EvalCase) -> dict[str, Any]:
    """A schema-valid, correct-by-construction candidate output for a case."""
    exp = case.expected
    ev = _first_evidence(case)
    deadline = dict(exp.get("deadline") or {"date": None, "kind": "none"})
    date_val = deadline.get("date")
    kind_val = deadline.get("kind", "none")
    request_id = case.input.get("request_id", case.case_id)
    return {
        "summary": f"Structured triage for request {request_id}.",
        "tasks": [
            {
                "task_id": "t1",
                "description": "Follow up on the request per the triage assessment.",
                "owner_role": None,
                "due_date": date_val,
                "evidence_refs": ev,
            }
        ],
        "deadline": {"date": date_val, "kind": kind_val, "evidence_refs": ev if date_val else []},
        "risk_level": exp.get("risk_level", "low"),
        "risk_reasons": [
            {
                "code": "assessed_from_request",
                "description": "Risk assessed from the request content.",
                "evidence_refs": ev,
            }
        ],
        "missing_information": [
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "reason": "Not provided in the request.",
                "evidence_refs": ev,
            }
            for key in exp.get("missing_information", [])
        ],
        "needs_attention": bool(exp.get("needs_attention", False)),
        "material_claims": [
            {"claim": "The triage summary reflects the request content.", "evidence_refs": ev}
        ],
    }


class _RecordedTarget(TargetAdapter):
    """Base for recorded fixtures: serialize ``_output`` and wrap it in an evidence envelope."""

    adapter_version = "v1"

    def _output(self, case: EvalCase) -> dict[str, Any] | str:
        raise NotImplementedError

    def invoke(self, case: EvalCase, ctx: InvocationContext) -> TargetInvocationResult:
        produced = self._output(case)
        raw = (
            produced
            if isinstance(produced, str)
            else json.dumps(produced, sort_keys=True, ensure_ascii=False)
        )
        return TargetInvocationResult(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            target_workflow_ref=case.workflow_ref,
            request_hash=content_hash(case.input),
            raw_output=raw,
            attempts=[Attempt(number=1, latency_ms=0.0)],
            usage={"input_tokens": 0, "output_tokens": 0},
            latency_ms=0.0,
            config_refs={"kind": "recorded"},
        )


class RecordedPass(_RecordedTarget):
    """Known-good baseline: a correct, schema-valid output."""

    adapter_id = "recorded_pass"

    def _output(self, case: EvalCase) -> dict[str, Any]:
        return build_correct_output(case)


class RecordedMissingInformationRegression(_RecordedTarget):
    """Valid schema, but drops all missing-information items (recall regression)."""

    adapter_id = "recorded_missing_information_regression"

    def _output(self, case: EvalCase) -> dict[str, Any]:
        out = build_correct_output(case)
        out["missing_information"] = []
        return out


class RecordedDeadlineRegression(_RecordedTarget):
    """Shifts an explicit deadline by one day, or invents one where there is none."""

    adapter_id = "recorded_deadline_regression"

    def _output(self, case: EvalCase) -> dict[str, Any]:
        out = build_correct_output(case)
        current = out["deadline"]["date"]
        if current:
            shifted = (date.fromisoformat(current) + timedelta(days=1)).isoformat()
            out["deadline"]["date"] = shifted
            out["tasks"][0]["due_date"] = shifted
        else:
            out["deadline"] = {
                "date": "2026-01-01",
                "kind": "inferred",
                "evidence_refs": out["deadline"]["evidence_refs"],
            }
        return out


class RecordedEvidenceRegression(_RecordedTarget):
    """Valid schema, but cites evidence references that do not exist in the case."""

    adapter_id = "recorded_evidence_regression"

    def _output(self, case: EvalCase) -> dict[str, Any]:
        out = build_correct_output(case)
        bad = ["nonexistent#span-999"]
        out["deadline"]["evidence_refs"] = bad
        for claim in out["material_claims"]:
            claim["evidence_refs"] = bad
        return out


class RecordedSchemaFailure(_RecordedTarget):
    """Schema-invalid output: an out-of-enum risk level and a dropped required field."""

    adapter_id = "recorded_schema_failure"

    def _output(self, case: EvalCase) -> dict[str, Any]:
        out = build_correct_output(case)
        out["risk_level"] = "severe"  # not in {low, medium, high}
        out.pop("needs_attention", None)  # required field missing
        return out


_ALL: list[_RecordedTarget] = [
    RecordedPass(),
    RecordedMissingInformationRegression(),
    RecordedDeadlineRegression(),
    RecordedEvidenceRegression(),
    RecordedSchemaFailure(),
]

RECORDED_TARGETS: dict[str, TargetAdapter] = {t.adapter_id: t for t in _ALL}


def get_recorded_target(adapter_id: str) -> TargetAdapter:
    try:
        return RECORDED_TARGETS[adapter_id]
    except KeyError:
        raise KeyError(
            f"unknown recorded target '{adapter_id}'; known: {sorted(RECORDED_TARGETS)}"
        ) from None
