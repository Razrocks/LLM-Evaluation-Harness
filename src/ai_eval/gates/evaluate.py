"""Deterministic gate evaluation.

Applies a versioned :class:`GatePolicy` to a run's metrics (and optionally a baseline
comparison) and returns ``PASS`` / ``FAIL`` / ``INVALID`` with **per-rule evidence**.

``INVALID`` is not a soft pass: it means the run could not be judged (a required metric was
absent, a supplied baseline comparison was incompatible, or the sample was too small).

A rule marked ``requires_baseline`` that is evaluated with **no baseline at all** is
``SKIPPED``, not ``INVALID`` — running without a baseline is a deliberate operator choice (it
is how the baseline run itself is gated), whereas supplying an *incompatible* baseline is a
genuine "cannot judge". Skipped rules never affect the outcome.

Precedence follows the spec's rule order: an unjudgeable run is INVALID before anything else,
then critical rules, then quality floors, then deltas and operational budgets.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.baselines import ComparisonReport
from ai_eval.domain import GateOutcome, GateRuleType, Severity
from ai_eval.metrics import MetricSummary

from .policy import GatePolicy, GateRule

# CLI exit codes (documented contract).
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INVALID = 2


class RuleStatus(StrEnum):
    """Per-rule outcome. ``SKIPPED`` = not applicable to this run; never affects the gate."""

    PASS = "pass"
    FAIL = "fail"
    INVALID = "invalid"
    SKIPPED = "skipped"


class RuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    type: GateRuleType
    severity: Severity
    status: RuleStatus
    metric: str | None = None
    observed: float | None = None
    threshold: float | None = None
    message: str


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str
    gate_version: str
    outcome: GateOutcome
    rule_results: list[RuleResult] = Field(default_factory=list)
    passed_rules: int = 0
    failed_rules: int = 0
    invalid_rules: int = 0
    skipped_rules: int = 0

    @property
    def exit_code(self) -> int:
        if self.outcome is GateOutcome.PASS:
            return EXIT_PASS
        return EXIT_FAIL if self.outcome is GateOutcome.FAIL else EXIT_INVALID


def _rr(rule: GateRule, status: RuleStatus, message: str, *, observed: float | None = None,
        threshold: float | None = None) -> RuleResult:
    return RuleResult(
        rule_id=rule.rule_id, type=rule.type, severity=rule.severity, status=status,
        metric=rule.metric, observed=observed, threshold=threshold, message=message,
    )


def _metric_rule(rule: GateRule, summary: MetricSummary) -> RuleResult:
    metrics = summary.by_name()
    if rule.metric is None or rule.metric not in metrics:
        return _rr(rule, RuleStatus.INVALID, f"metric '{rule.metric}' not produced by this run")
    metric = metrics[rule.metric]
    if metric.value is None:
        return _rr(rule, RuleStatus.INVALID,
                   f"metric '{rule.metric}' has no value ({metric.missing_data_rule})")
    if rule.min_sample_size is not None and metric.denominator < rule.min_sample_size:
        return _rr(rule, RuleStatus.INVALID,
                   f"sample too small: n={metric.denominator} < {rule.min_sample_size}",
                   observed=metric.value)
    if rule.type is GateRuleType.REQUIRED_METRIC_PRESENT:
        return _rr(rule, RuleStatus.PASS, "metric present", observed=metric.value)
    if rule.type is GateRuleType.METRIC_MINIMUM:
        threshold = rule.minimum
        if threshold is None:
            return _rr(rule, RuleStatus.INVALID, "rule has no 'minimum'")
        ok = metric.value >= threshold
        return _rr(rule, RuleStatus.PASS if ok else RuleStatus.FAIL,
                   f"{rule.metric}={metric.value} {'>=' if ok else '<'} {threshold}",
                   observed=metric.value, threshold=threshold)
    threshold = rule.maximum
    if threshold is None:
        return _rr(rule, RuleStatus.INVALID, "rule has no 'maximum'")
    ok = metric.value <= threshold
    return _rr(rule, RuleStatus.PASS if ok else RuleStatus.FAIL,
               f"{rule.metric}={metric.value} {'<=' if ok else '>'} {threshold}",
               observed=metric.value, threshold=threshold)


def _delta_rule(rule: GateRule, comparison: ComparisonReport | None) -> RuleResult:
    if comparison is None:
        if rule.requires_baseline:
            return _rr(rule, RuleStatus.SKIPPED, "no baseline supplied; rule not applicable")
        return _rr(rule, RuleStatus.INVALID, "baseline comparison required but not supplied")
    if not comparison.compatible:
        return _rr(rule, RuleStatus.INVALID,
                   f"baseline comparison is incompatible: {'; '.join(comparison.warnings)}")
    if rule.metric is None:
        return _rr(rule, RuleStatus.INVALID, "rule has no 'metric'")
    delta = comparison.delta_for(rule.metric)
    if delta is None:
        return _rr(rule, RuleStatus.INVALID, f"no comparable delta for '{rule.metric}'")
    if rule.type is GateRuleType.BASELINE_DELTA_MINIMUM:
        threshold = rule.minimum_delta
        if threshold is None:
            return _rr(rule, RuleStatus.INVALID, "rule has no 'minimum_delta'")
        ok = delta >= threshold
        return _rr(rule, RuleStatus.PASS if ok else RuleStatus.FAIL,
                   f"delta({rule.metric})={delta:.4f} {'>=' if ok else '<'} {threshold}",
                   observed=delta, threshold=threshold)
    threshold = rule.maximum_delta
    if threshold is None:
        return _rr(rule, RuleStatus.INVALID, "rule has no 'maximum_delta'")
    ok = delta <= threshold
    return _rr(rule, RuleStatus.PASS if ok else RuleStatus.FAIL,
               f"delta({rule.metric})={delta:.4f} {'<=' if ok else '>'} {threshold}",
               observed=delta, threshold=threshold)


def _critical_rule(rule: GateRule, summary: MetricSummary) -> RuleResult:
    observed = float(summary.critical_case_failures)
    threshold = float(rule.maximum if rule.maximum is not None else 0)
    ok = observed <= threshold
    return _rr(rule, RuleStatus.PASS if ok else RuleStatus.FAIL,
               f"critical-case failures={int(observed)} {'<=' if ok else '>'} {int(threshold)}",
               observed=observed, threshold=threshold)


def evaluate_gate(
    policy: GatePolicy,
    summary: MetricSummary,
    comparison: ComparisonReport | None = None,
) -> GateResult:
    results: list[RuleResult] = []
    for rule in policy.rules:
        if rule.type is GateRuleType.CRITICAL_CASE_COUNT_MAX:
            results.append(_critical_rule(rule, summary))
        elif rule.type in (GateRuleType.BASELINE_DELTA_MINIMUM, GateRuleType.BASELINE_DELTA_MAXIMUM):
            results.append(_delta_rule(rule, comparison))
        else:
            results.append(_metric_rule(rule, summary))

    invalid = sum(1 for r in results if r.status is RuleStatus.INVALID)
    failed = sum(1 for r in results if r.status is RuleStatus.FAIL)
    passed = sum(1 for r in results if r.status is RuleStatus.PASS)
    skipped = sum(1 for r in results if r.status is RuleStatus.SKIPPED)

    if invalid:
        outcome = GateOutcome.INVALID  # an unjudgeable run is never a pass
    elif failed:
        outcome = GateOutcome.FAIL
    else:
        outcome = GateOutcome.PASS

    return GateResult(
        gate_id=policy.gate_id, gate_version=policy.gate_version, outcome=outcome,
        rule_results=results, passed_rules=passed, failed_rules=failed,
        invalid_rules=invalid, skipped_rules=skipped,
    )
