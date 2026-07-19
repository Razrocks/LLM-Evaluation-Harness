"""Metric aggregation with honest denominators.

Every metric records its numerator, denominator, aggregation method, and missing-data rule —
there is no bare "0.9" here. Invocation errors are excluded from *quality* numerators and
surface under contract/operational metrics with their own denominators. Risk macro-F1 and the
confusion matrix use scikit-learn so the classification math is trusted, not hand-rolled.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field
from sklearn.metrics import confusion_matrix, f1_score, recall_score

from ai_eval.domain import AssertionResultStatus, CaseExecutionState, Criticality
from ai_eval.scoring import AssertionResult, CaseScore

RISK_LABELS = ["low", "medium", "high"]


@dataclass
class CaseMetricInput:
    """Everything the aggregator needs about one scored case execution."""

    case_id: str
    criticality: Criticality
    invoked_ok: bool
    parse_ok: bool
    schema_ok: bool
    expected_risk: str | None
    observed_risk: str | None
    score: CaseScore
    results: list[AssertionResult] = field(default_factory=list)


class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "v1"
    value: float | None
    numerator: float | None
    denominator: int
    aggregation: str
    scope: str = "run"
    missing_data_rule: str
    detail: dict = Field(default_factory=dict)


class MetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int
    metrics: list[Metric]
    risk_confusion_matrix: dict = Field(default_factory=dict)
    critical_case_failures: int = 0

    def by_name(self) -> dict[str, Metric]:
        return {m.name: m for m in self.metrics}


def _base(scorer_ref: str) -> str:
    return scorer_ref.split(".v")[0]


def _rate(name: str, num: int, den: int, rule: str, detail: dict | None = None) -> Metric:
    return Metric(
        name=name,
        value=(num / den) if den else None,
        numerator=num,
        denominator=den,
        aggregation="rate",
        missing_data_rule=rule,
        detail=detail or {},
    )


def _results_of(inputs: list[CaseMetricInput], scorer_base: str) -> list[AssertionResult]:
    return [r for ci in inputs for r in ci.results if _base(r.scorer_ref) == scorer_base]


def _accuracy_from(results: list[AssertionResult], name: str) -> Metric:
    evaluable = [r for r in results if r.status in (AssertionResultStatus.PASS, AssertionResultStatus.FAIL)]
    passes = sum(1 for r in evaluable if r.status is AssertionResultStatus.PASS)
    return _rate(name, passes, len(evaluable), "unevaluable/error results excluded")


def _missing_info_micro(inputs: list[CaseMetricInput]) -> list[Metric]:
    tp = fp = fn = 0
    for r in _results_of(inputs, "set_precision_recall_f1"):
        expected = set(r.expected or []) if isinstance(r.expected, list) else set()
        observed = set(r.observed or []) if isinstance(r.observed, list) else set()
        tp += len(expected & observed)
        fp += len(observed - expected)
        fn += len(expected - observed)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision and recall and (precision + recall)
        else (0.0 if (tp + fp + fn) else None)
    )
    rule = "micro-averaged over missing-information assertions; empty when none present"
    return [
        Metric(name="missing_information_precision", value=precision, numerator=tp,
               denominator=tp + fp, aggregation="micro_precision", missing_data_rule=rule),
        Metric(name="missing_information_recall", value=recall, numerator=tp,
               denominator=tp + fn, aggregation="micro_recall", missing_data_rule=rule),
        Metric(name="missing_information_f1", value=f1, numerator=None,
               denominator=tp + fp + fn, aggregation="micro_f1", missing_data_rule=rule),
    ]


def _risk_metrics(inputs: list[CaseMetricInput]) -> tuple[list[Metric], dict]:
    pairs = [
        (ci.expected_risk, ci.observed_risk)
        for ci in inputs
        if ci.expected_risk in RISK_LABELS and ci.observed_risk in RISK_LABELS
    ]
    rule = "cases with an approved risk label and a parsed risk_level"
    if not pairs:
        empty = [
            Metric(name=n, value=None, numerator=None, denominator=0, aggregation=a,
                   missing_data_rule=rule)
            for n, a in [("risk_accuracy", "rate"), ("risk_macro_f1", "macro_f1"),
                         ("risk_recall.high", "recall")]
        ]
        return empty, {}
    y_true = [e for e, _ in pairs]
    y_pred = [o for _, o in pairs]
    correct = sum(1 for e, o in pairs if e == o)
    macro_f1 = float(f1_score(y_true, y_pred, labels=RISK_LABELS, average="macro", zero_division=0))
    high_recall = float(
        recall_score(y_true, y_pred, labels=["high"], average="macro", zero_division=0)
    )
    cm = confusion_matrix(y_true, y_pred, labels=RISK_LABELS).tolist()
    metrics = [
        _rate("risk_accuracy", correct, len(pairs), rule),
        Metric(name="risk_macro_f1", value=macro_f1, numerator=None, denominator=len(pairs),
               aggregation="macro_f1", missing_data_rule=rule),
        Metric(name="risk_recall.high", value=high_recall, numerator=None,
               denominator=sum(1 for e, _ in pairs if e == "high"),
               aggregation="recall", missing_data_rule=rule),
    ]
    return metrics, {"labels": RISK_LABELS, "matrix": cm}


def aggregate_metrics(inputs: list[CaseMetricInput]) -> MetricSummary:
    total = len(inputs)
    invoked = sum(1 for ci in inputs if ci.invoked_ok)
    parsed = sum(1 for ci in inputs if ci.parse_ok)
    schema_ok = sum(1 for ci in inputs if ci.schema_ok)

    metrics: list[Metric] = [
        _rate("invocation_success_rate", invoked, total, "all cases in the denominator"),
        _rate("parse_success_rate", parsed, invoked,
              "denominator = successfully invoked cases; invocation errors excluded"),
        _rate("schema_pass_rate", schema_ok, invoked,
              "denominator = successfully invoked cases; invocation errors excluded"),
        _accuracy_from(_results_of(inputs, "normalized_date_equal"), "deadline_accuracy"),
        _accuracy_from(_results_of(inputs, "deadline_kind_equal"), "deadline_kind_accuracy"),
        _accuracy_from(_results_of(inputs, "boolean_equal"), "needs_attention_accuracy"),
    ]

    risk_metrics, confusion = _risk_metrics(inputs)
    metrics.extend(risk_metrics)
    metrics.extend(_missing_info_micro(inputs))

    ev = _results_of(inputs, "evidence_reference_valid")
    ev_pass = sum(1 for r in ev if r.status is AssertionResultStatus.PASS)
    metrics.append(_rate("evidence_reference_validity", ev_pass, len(ev),
                         "denominator = evidence-reference assertions"))

    unsup = _results_of(inputs, "unsupported_material_claim_absent")
    unsup_fail = sum(1 for r in unsup if r.status is AssertionResultStatus.FAIL)
    metrics.append(_rate("unsupported_material_claim_rate", unsup_fail, len(unsup),
                         "denominator = unsupported-claim assertions; higher is worse"))

    critical_failures = sum(1 for ci in inputs if ci.score.is_critical_failure)
    metrics.append(
        Metric(name="cases_passed", value=(sum(1 for ci in inputs if ci.score.passed) / total)
               if total else None,
               numerator=sum(1 for ci in inputs if ci.score.passed), denominator=total,
               aggregation="rate", missing_data_rule="all cases",
               detail={"passed": sum(1 for ci in inputs if ci.score.passed)})
    )

    return MetricSummary(
        total_cases=total,
        metrics=metrics,
        risk_confusion_matrix=confusion,
        critical_case_failures=critical_failures,
    )


def build_metric_input(
    case_id: str,
    criticality: Criticality,
    *,
    invoked_ok: bool,
    expected_risk: str | None,
    observed_risk: str | None,
    score: CaseScore,
) -> CaseMetricInput:
    parse_ok = score.state not in (
        CaseExecutionState.PARSE_ERROR,
        CaseExecutionState.INVOCATION_ERROR,
    )
    schema_ok = score.state not in (
        CaseExecutionState.PARSE_ERROR,
        CaseExecutionState.SCHEMA_ERROR,
        CaseExecutionState.INVOCATION_ERROR,
    )
    return CaseMetricInput(
        case_id=case_id,
        criticality=criticality,
        invoked_ok=invoked_ok,
        parse_ok=parse_ok and invoked_ok,
        schema_ok=schema_ok and invoked_ok,
        expected_risk=expected_risk,
        observed_risk=observed_risk,
        score=score,
        results=score.results,
    )
