"""Hand-calculated metric fixtures with denominator checks and a scikit-learn cross-check."""

from __future__ import annotations

from sklearn.metrics import f1_score

from ai_eval.domain import AssertionResultStatus, CaseExecutionState, Criticality
from ai_eval.metrics import aggregate_metrics, build_metric_input
from ai_eval.parsing import ParseStatus
from ai_eval.scoring import AssertionResult, CaseScore


def _case_score(results=None, state=CaseExecutionState.PASSED, crit=Criticality.NORMAL) -> CaseScore:
    return CaseScore(
        case_id="c", case_version=1, criticality=crit, state=state,
        parse_status=ParseStatus.PARSED, results=results or [],
    )


def _mi(expected_risk, observed_risk, *, results=None, state=CaseExecutionState.PASSED,
        crit=Criticality.NORMAL, invoked_ok=True):
    return build_metric_input(
        "c", crit, invoked_ok=invoked_ok, expected_risk=expected_risk,
        observed_risk=observed_risk, score=_case_score(results, state, crit),
    )


def test_risk_accuracy_high_recall_and_macro_f1() -> None:
    inputs = [_mi("high", "medium"), _mi("high", "high"), _mi("low", "low")]
    m = aggregate_metrics(inputs).by_name()
    assert m["risk_accuracy"].numerator == 2
    assert m["risk_accuracy"].denominator == 3
    assert m["risk_recall.high"].value == 0.5  # 1 of 2 high cases recalled
    expected = f1_score(
        ["high", "high", "low"], ["medium", "high", "low"],
        labels=["low", "medium", "high"], average="macro", zero_division=0,
    )
    assert abs((m["risk_macro_f1"].value or 0) - expected) < 1e-9


def test_missing_information_micro_precision_recall() -> None:
    result = AssertionResult(
        assertion_id="mi", scorer_ref="set_precision_recall_f1.v1",
        status=AssertionResultStatus.FAIL, expected=["a", "b"], observed=["a"],
    )
    m = aggregate_metrics([_mi("low", "low", results=[result])]).by_name()
    assert m["missing_information_recall"].value == 0.5  # tp=1, fn=1
    assert m["missing_information_precision"].value == 1.0  # tp=1, fp=0


def test_schema_pass_rate_excludes_invocation_errors() -> None:
    inputs = [_mi("low", "low"), _mi("low", "low"), _mi("low", "low")]
    inputs.append(_mi("low", None, state=CaseExecutionState.INVOCATION_ERROR, invoked_ok=False))
    m = aggregate_metrics(inputs).by_name()
    assert m["invocation_success_rate"].numerator == 3
    assert m["invocation_success_rate"].denominator == 4
    # quality denominator excludes the invocation error
    assert m["schema_pass_rate"].denominator == 3
    assert m["schema_pass_rate"].value == 1.0


def test_empty_denominator_is_none_not_zero() -> None:
    m = aggregate_metrics([_mi(None, None)]).by_name()
    assert m["risk_accuracy"].value is None
    assert m["risk_accuracy"].denominator == 0


def test_critical_case_failure_counted() -> None:
    crit = _mi("high", "medium", state=CaseExecutionState.FAILED_ASSERTIONS,
               crit=Criticality.CRITICAL)
    summary = aggregate_metrics([crit])
    assert summary.critical_case_failures == 1
