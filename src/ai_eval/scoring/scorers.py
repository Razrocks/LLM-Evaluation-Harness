"""The versioned scorer registry.

Each scorer is a pure function ``(Assertion, ScoringContext) -> AssertionResult``. Scorers are
registered by ``scorer_ref`` (name + version); an assertion names exactly one. Deterministic by
construction: same inputs, same version, same result. Failure codes come from the controlled
taxonomy so a failure can always be classified.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from ai_eval.domain import Assertion, AssertionResultStatus, FailureCode, OnUnevaluable

from .context import ScoringContext
from .normalize import NORMALIZER_VERSION, DateNormalizationError, normalize_iso_date
from .result import AssertionResult, failure
from .selectors import MISSING, resolve_selector
from .vocab import normalize_missing_info_key

Scorer = Callable[[Assertion, ScoringContext], AssertionResult]

_PASS = AssertionResultStatus.PASS
_FAIL = AssertionResultStatus.FAIL
_ERROR = AssertionResultStatus.ERROR
_UNEVAL = AssertionResultStatus.UNEVALUABLE

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
_MONEY = re.compile(r"(?:CAD|USD|EUR|GBP|C\$|US\$|\$|£|€)\s?\d[\d,]*(?:\.\d+)?", re.IGNORECASE)


# --- result builders ----------------------------------------------------------------------


def _mk(
    assertion: Assertion,
    status: AssertionResultStatus,
    *,
    score: float | None = None,
    expected: object = None,
    observed: object = None,
    codes: list[FailureCode] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    normalization: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion.assertion_id,
        scorer_ref=assertion.scorer_ref,
        status=status,
        score=score,
        threshold=assertion.pass_threshold,
        expected=expected,
        observed=observed,
        normalization=normalization or [],
        evidence=evidence or [],
        failure_codes=failure(codes) if codes else [],
        severity=assertion.severity,
        metadata=metadata or {},
    )


def _unevaluable(assertion: Assertion, reason: str) -> AssertionResult:
    """Apply the assertion's declared ``on_unevaluable`` policy."""
    if assertion.on_unevaluable is OnUnevaluable.FAIL:
        return _mk(assertion, _FAIL, score=0.0, metadata={"unevaluable_reason": reason})
    if assertion.on_unevaluable is OnUnevaluable.ERROR:
        return _mk(assertion, _ERROR, metadata={"unevaluable_reason": reason})
    return _mk(assertion, _UNEVAL, metadata={"unevaluable_reason": reason})


def _selector_value(output: dict[str, Any], selector: str | None) -> object:
    if not selector:
        return MISSING
    value = resolve_selector(output, selector)
    return None if value is MISSING else value


def _all_evidence_refs(output: dict[str, Any]) -> list[tuple[str, str]]:
    """Every (field, evidence_ref) pair present in a triage output."""
    refs: list[tuple[str, str]] = []
    for r in (output.get("deadline") or {}).get("evidence_refs", []) or []:
        refs.append(("deadline", r))
    for t in output.get("tasks", []) or []:
        for r in t.get("evidence_refs", []) or []:
            refs.append((f"task:{t.get('task_id')}", r))
    for rr in output.get("risk_reasons", []) or []:
        for r in rr.get("evidence_refs", []) or []:
            refs.append(("risk_reason", r))
    for mi in output.get("missing_information", []) or []:
        for r in mi.get("evidence_refs", []) or []:
            refs.append(("missing_information", r))
    for mc in output.get("material_claims", []) or []:
        for r in mc.get("evidence_refs", []) or []:
            refs.append(("material_claim", r))
    return refs


# --- scorers ------------------------------------------------------------------------------


def score_schema_valid(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    if ctx.parse.ok:
        return _mk(assertion, _PASS, score=1.0, observed="valid")
    code = ctx.parse.failure_code
    return _mk(
        assertion,
        _FAIL,
        score=0.0,
        observed=str(ctx.parse.status),
        codes=[code] if code else None,
        evidence=[{"message": ctx.parse.message, "errors": ctx.parse.errors}],
    )


def score_normalized_date_equal(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    observed_raw = _selector_value(out, assertion.observed_selector)
    observed_str = observed_raw if isinstance(observed_raw, str) or observed_raw is None else None
    norm = [{"normalizer_version": NORMALIZER_VERSION}]
    try:
        obs_date = normalize_iso_date(observed_str)
    except DateNormalizationError as exc:
        return _mk(
            assertion, _FAIL, score=0.0, expected=assertion.expected, observed=observed_str,
            codes=[FailureCode.DEADLINE_MISSED], normalization=norm,
            evidence=[{"normalization_error": str(exc)}],
        )
    exp_date = normalize_iso_date(assertion.expected)
    if exp_date == obs_date:
        return _mk(
            assertion, _PASS, score=1.0, expected=assertion.expected, observed=observed_str,
            normalization=norm,
        )
    if exp_date is not None and obs_date is None:
        codes = [FailureCode.DEADLINE_FALSE_NEGATIVE]
    elif exp_date is None and obs_date is not None:
        codes = [FailureCode.DEADLINE_FALSE_POSITIVE]
    else:
        codes = [FailureCode.DEADLINE_MISSED]
    return _mk(
        assertion, _FAIL, score=0.0, expected=assertion.expected, observed=observed_str,
        codes=codes, normalization=norm,
    )


def score_categorical_equal(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    observed = _selector_value(out, assertion.observed_selector)
    if observed == assertion.expected:
        return _mk(assertion, _PASS, score=1.0, expected=assertion.expected, observed=observed)
    codes: list[FailureCode] = []
    sel = assertion.observed_selector or ""
    if sel.endswith("risk_level") and observed in _RISK_ORDER and assertion.expected in _RISK_ORDER:
        codes = [
            FailureCode.RISK_UNDERCLASSIFIED
            if _RISK_ORDER[str(observed)] < _RISK_ORDER[str(assertion.expected)]
            else FailureCode.RISK_OVERCLASSIFIED
        ]
    return _mk(
        assertion, _FAIL, score=0.0, expected=assertion.expected, observed=observed, codes=codes
    )


def score_deadline_kind_equal(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    observed = _selector_value(out, assertion.observed_selector)
    status = _PASS if observed == assertion.expected else _FAIL
    return _mk(
        assertion, status, score=1.0 if status is _PASS else 0.0,
        expected=assertion.expected, observed=observed,
    )


def score_boolean_equal(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    observed = _selector_value(out, assertion.observed_selector)
    if observed == assertion.expected:
        return _mk(assertion, _PASS, score=1.0, expected=assertion.expected, observed=observed)
    codes = (
        [FailureCode.NEEDS_ATTENTION_INCORRECT]
        if (assertion.observed_selector or "").endswith("needs_attention")
        else []
    )
    return _mk(
        assertion, _FAIL, score=0.0, expected=assertion.expected, observed=observed, codes=codes
    )


def score_set_precision_recall_f1(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    raw = resolve_selector(out, assertion.observed_selector or "$")
    raw_items = [x for x in raw if x is not MISSING and isinstance(x, str)] if isinstance(raw, list) else []
    norm_notes: list[dict] = []
    observed_keys: set[str] = set()
    for item in raw_items:
        key, alias = normalize_missing_info_key(item)
        observed_keys.add(key)
        if alias:
            norm_notes.append({"alias": alias, "canonical": key})
    expected_keys = set(assertion.expected or [])
    tp = observed_keys & expected_keys
    precision = len(tp) / len(observed_keys) if observed_keys else (1.0 if not expected_keys else 0.0)
    recall = len(tp) / len(expected_keys) if expected_keys else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    min_recall = float(assertion.params.get("minimum_recall", 1.0))
    min_precision = float(assertion.params.get("minimum_precision", 0.0))
    omitted = sorted(expected_keys - observed_keys)
    spurious = sorted(observed_keys - expected_keys)
    passed = recall >= min_recall and precision >= min_precision
    codes: list[FailureCode] = []
    if not passed:
        if omitted:
            codes.append(FailureCode.MISSING_INFO_OMITTED)
        if spurious:
            codes.append(FailureCode.MISSING_INFO_SPURIOUS)
    return _mk(
        assertion, _PASS if passed else _FAIL, score=f1,
        expected=sorted(expected_keys), observed=sorted(observed_keys), codes=codes,
        normalization=norm_notes,
        metadata={
            "precision": precision, "recall": recall, "f1": f1,
            "omitted": omitted, "spurious": spurious,
            "minimum_recall": min_recall, "minimum_precision": min_precision,
        },
    )


def score_required_task_coverage(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    required = list(assertion.expected or [])
    if not required:
        return _mk(assertion, _PASS, score=1.0, metadata={"required": []})
    tasks = [
        (str(t.get("task_id", "")), str(t.get("description", "")).lower())
        for t in out.get("tasks", []) or []
    ]
    covered, missing = [], []
    for req in required:
        needle = str(req).lower()
        if any(needle in desc or str(req) == tid for tid, desc in tasks):
            covered.append(req)
        else:
            missing.append(req)
    score = len(covered) / len(required)
    status = _PASS if not missing else _FAIL
    return _mk(
        assertion, status, score=score, expected=required, observed=[t[0] for t in tasks],
        codes=[FailureCode.TASK_UNSUPPORTED] if missing else None,
        metadata={"covered": covered, "missing": missing},
    )


def score_evidence_reference_valid(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    refs = _all_evidence_refs(out)
    if not refs:
        return _mk(assertion, _PASS, score=1.0, metadata={"total_refs": 0})
    invalid = [{"field": f, "ref": r} for f, r in refs if not ctx.evidence.is_valid_ref(r)]
    score = (len(refs) - len(invalid)) / len(refs)
    if invalid:
        return _mk(
            assertion, _FAIL, score=score, codes=[FailureCode.INVALID_EVIDENCE_REFERENCE],
            evidence=invalid, metadata={"total_refs": len(refs), "invalid_refs": len(invalid)},
        )
    return _mk(assertion, _PASS, score=1.0, metadata={"total_refs": len(refs)})


def score_evidence_span_support(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    claims = out.get("material_claims", []) or []
    unsupported = []
    for claim in claims:
        text = str(claim.get("claim", ""))
        refs = claim.get("evidence_refs", []) or []
        if not any(ctx.evidence.supports_value(r, text) for r in refs):
            unsupported.append(text)
    if unsupported:
        return _mk(
            assertion, _FAIL, score=0.0, codes=[FailureCode.EVIDENCE_MISMATCH],
            evidence=[{"unsupported_claim": c} for c in unsupported],
        )
    return _mk(assertion, _PASS, score=1.0, metadata={"claims": len(claims)})


def score_unsupported_material_claim_absent(
    assertion: Assertion, ctx: ScoringContext
) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    unsupported = []
    for claim in out.get("material_claims", []) or []:
        text = str(claim.get("claim", ""))
        refs = claim.get("evidence_refs", []) or []
        amounts = [m.group(0) for m in _MONEY.finditer(text)]
        if amounts:
            supported = any(ctx.evidence.supports_value(r, amt) for r in refs for amt in amounts)
            if not supported:
                unsupported.append({"claim": text, "reason": "monetary amount not in cited sources"})
        elif not any(ctx.evidence.is_valid_ref(r) for r in refs):
            unsupported.append({"claim": text, "reason": "no valid evidence reference"})
    if unsupported:
        return _mk(
            assertion, _FAIL, score=0.0, codes=[FailureCode.UNSUPPORTED_MATERIAL_CLAIM],
            evidence=unsupported,
        )
    return _mk(assertion, _PASS, score=1.0)


def score_prohibited_value_absent(assertion: Assertion, ctx: ScoringContext) -> AssertionResult:
    out = ctx.output
    if out is None:
        return _unevaluable(assertion, "no parsed output")
    prohibited = [str(p) for p in assertion.params.get("prohibited", [])]
    haystack = json.dumps(out, ensure_ascii=False).lower()
    found = [p for p in prohibited if p.lower() in haystack]
    if found:
        # No dedicated taxonomy code for a prohibited literal; the evidence carries the detail.
        return _mk(assertion, _FAIL, score=0.0, evidence=[{"prohibited_found": found}])
    return _mk(assertion, _PASS, score=1.0, metadata={"checked": len(prohibited)})


SCORERS: dict[str, Scorer] = {
    "schema_valid.v1": score_schema_valid,
    "normalized_date_equal.v1": score_normalized_date_equal,
    "deadline_kind_equal.v1": score_deadline_kind_equal,
    "categorical_equal.v1": score_categorical_equal,
    "boolean_equal.v1": score_boolean_equal,
    "set_precision_recall_f1.v1": score_set_precision_recall_f1,
    "required_task_coverage.v1": score_required_task_coverage,
    "evidence_reference_valid.v1": score_evidence_reference_valid,
    "evidence_span_support.v1": score_evidence_span_support,
    "unsupported_material_claim_absent.v1": score_unsupported_material_claim_absent,
    "prohibited_value_absent.v1": score_prohibited_value_absent,
}


def get_scorer(scorer_ref: str) -> Scorer | None:
    return SCORERS.get(scorer_ref)
