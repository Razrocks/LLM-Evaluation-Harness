"""Gate rule semantics: thresholds, precedence, INVALID vs SKIPPED, and exit codes."""

from __future__ import annotations

from ai_eval.baselines import ComparisonReport, MetricDelta
from ai_eval.domain import GateOutcome, GateRuleType, Severity
from ai_eval.gates import (
    EXIT_FAIL,
    EXIT_INVALID,
    EXIT_PASS,
    GatePolicy,
    GateRule,
    RuleStatus,
    evaluate_gate,
)
from ai_eval.metrics import Metric, MetricSummary


def _summary(critical: int = 0, denominator: int = 10, **values: float | None) -> MetricSummary:
    metrics = [
        Metric(name=name, value=value, numerator=None, denominator=denominator,
               aggregation="rate", missing_data_rule="test fixture")
        for name, value in values.items()
    ]
    return MetricSummary(total_cases=10, metrics=metrics, critical_case_failures=critical)


def _policy(*rules: GateRule) -> GatePolicy:
    return GatePolicy(gate_id="g", gate_version="1.0.0", rules=list(rules))


def _rule(rule_id: str, rtype: GateRuleType, **kw: object) -> GateRule:
    kw.setdefault("severity", Severity.MAJOR)
    return GateRule(rule_id=rule_id, type=rtype, **kw)  # type: ignore[arg-type]


def _comparison(compatible: bool = True, **deltas: float | None) -> ComparisonReport:
    return ComparisonReport(
        baseline_id="b", baseline_run_id="r0", candidate_run_id="r1",
        compatible=compatible,
        warnings=[] if compatible else ["dataset release mismatch"],
        deltas=[
            MetricDelta(metric=k, baseline_value=None, candidate_value=None, delta=v)
            for k, v in deltas.items()
        ],
    )


def test_metric_minimum_pass() -> None:
    result = evaluate_gate(
        _policy(_rule("floor", GateRuleType.METRIC_MINIMUM, metric="m", minimum=0.9)),
        _summary(m=0.95),
    )
    assert result.outcome is GateOutcome.PASS
    assert result.exit_code == EXIT_PASS


def test_metric_minimum_fail() -> None:
    result = evaluate_gate(
        _policy(_rule("floor", GateRuleType.METRIC_MINIMUM, metric="m", minimum=0.9)),
        _summary(m=0.5),
    )
    assert result.outcome is GateOutcome.FAIL
    assert result.exit_code == EXIT_FAIL


def test_metric_maximum_fail() -> None:
    result = evaluate_gate(
        _policy(_rule("ceil", GateRuleType.METRIC_MAXIMUM, metric="m", maximum=0.0)),
        _summary(m=0.25),
    )
    assert result.outcome is GateOutcome.FAIL


def test_absent_metric_is_invalid_not_pass() -> None:
    result = evaluate_gate(
        _policy(_rule("floor", GateRuleType.METRIC_MINIMUM, metric="nope", minimum=0.9)),
        _summary(m=1.0),
    )
    assert result.outcome is GateOutcome.INVALID
    assert result.exit_code == EXIT_INVALID


def test_null_valued_metric_is_invalid() -> None:
    result = evaluate_gate(
        _policy(_rule("floor", GateRuleType.METRIC_MINIMUM, metric="m", minimum=0.9)),
        _summary(m=None),
    )
    assert result.outcome is GateOutcome.INVALID


def test_sample_too_small_is_invalid() -> None:
    result = evaluate_gate(
        _policy(_rule("floor", GateRuleType.METRIC_MINIMUM, metric="m", minimum=0.9,
                      min_sample_size=50)),
        _summary(m=1.0, denominator=10),
    )
    assert result.outcome is GateOutcome.INVALID


def test_critical_case_rule_blocks() -> None:
    result = evaluate_gate(
        _policy(_rule("crit", GateRuleType.CRITICAL_CASE_COUNT_MAX, maximum=0,
                      severity=Severity.CRITICAL)),
        _summary(critical=3, m=1.0),
    )
    assert result.outcome is GateOutcome.FAIL


def test_baseline_delta_rule_skipped_without_baseline() -> None:
    """requires_baseline + no comparison = not applicable, not unjudgeable."""
    result = evaluate_gate(
        _policy(_rule("delta", GateRuleType.BASELINE_DELTA_MINIMUM, metric="m",
                      minimum_delta=-0.03, requires_baseline=True)),
        _summary(m=1.0),
        None,
    )
    assert result.rule_results[0].status is RuleStatus.SKIPPED
    assert result.skipped_rules == 1
    assert result.outcome is GateOutcome.PASS


def test_baseline_delta_rule_fails_on_regression() -> None:
    result = evaluate_gate(
        _policy(_rule("delta", GateRuleType.BASELINE_DELTA_MINIMUM, metric="m",
                      minimum_delta=-0.03, requires_baseline=True)),
        _summary(m=0.0),
        _comparison(m=-1.0),
    )
    assert result.outcome is GateOutcome.FAIL


def test_incompatible_comparison_is_invalid() -> None:
    result = evaluate_gate(
        _policy(_rule("delta", GateRuleType.BASELINE_DELTA_MINIMUM, metric="m",
                      minimum_delta=-0.03, requires_baseline=True)),
        _summary(m=1.0),
        _comparison(compatible=False, m=0.0),
    )
    assert result.outcome is GateOutcome.INVALID


def test_invalid_beats_fail_in_precedence() -> None:
    """A run that cannot be judged is INVALID even when another rule already failed."""
    result = evaluate_gate(
        _policy(
            _rule("floor", GateRuleType.METRIC_MINIMUM, metric="m", minimum=0.9),
            _rule("missing", GateRuleType.METRIC_MINIMUM, metric="absent", minimum=0.9),
        ),
        _summary(m=0.1),
    )
    assert result.failed_rules == 1
    assert result.invalid_rules == 1
    assert result.outcome is GateOutcome.INVALID
