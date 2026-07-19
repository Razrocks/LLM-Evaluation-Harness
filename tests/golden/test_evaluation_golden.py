"""End-to-end golden checks: each recorded target produces the expected caught failures, and
reports are written and byte-for-byte reproducible."""

from __future__ import annotations

from pathlib import Path

from ai_eval.datasets import load_cases_dir
from ai_eval.evaluation import evaluate_raw_outputs
from ai_eval.reporting import write_evaluation_reports
from ai_eval.targets import InvocationContext, get_recorded_target

REPO = Path(__file__).resolve().parents[2]
CASES = load_cases_dir(REPO / "datasets/reference/request_triage/v1/cases")

REPORT_FILES = [
    "parsed_outputs.jsonl",
    "assertion_results.jsonl",
    "metric_summary.json",
    "metric_summary.csv",
    "failures.jsonl",
    "failure_report.md",
]


def _evaluate(target_name: str):
    adapter = get_recorded_target(target_name)
    items = []
    for case in CASES:
        result = adapter.invoke(
            case, InvocationContext(run_id="golden", case_execution_id=f"golden:{case.case_id}")
        )
        items.append((case, result.raw_output, result.succeeded))
    return evaluate_raw_outputs(items)


def _all_codes(evaluation) -> set[str]:
    return {code for f in evaluation.failures for code in f.failure_codes}


def test_recorded_pass_is_clean() -> None:
    ev = _evaluate("recorded_pass")
    metrics = ev.summary.by_name()
    assert metrics["cases_passed"].value == 1.0
    assert ev.summary.critical_case_failures == 0
    assert ev.failures == []


def test_missing_information_regression_caught() -> None:
    ev = _evaluate("recorded_missing_information_regression")
    metrics = ev.summary.by_name()
    assert metrics["schema_pass_rate"].value == 1.0  # still valid JSON
    assert metrics["missing_information_recall"].value == 0.0  # but recall collapsed
    assert "MISSING_INFO_OMITTED" in _all_codes(ev)


def test_deadline_regression_caught() -> None:
    ev = _evaluate("recorded_deadline_regression")
    accuracy = ev.summary.by_name()["deadline_accuracy"].value
    assert accuracy is not None and accuracy < 1.0
    assert "DEADLINE_MISSED" in _all_codes(ev)


def test_evidence_regression_caught() -> None:
    ev = _evaluate("recorded_evidence_regression")
    codes = _all_codes(ev)
    assert "UNSUPPORTED_MATERIAL_CLAIM" in codes or "INVALID_EVIDENCE_REFERENCE" in codes


def test_schema_failure_caught() -> None:
    ev = _evaluate("recorded_schema_failure")
    metrics = ev.summary.by_name()
    assert metrics["schema_pass_rate"].value == 0.0
    assert metrics["risk_accuracy"].value is None  # nothing parsed -> excluded, not zero
    assert "OUTPUT_SCHEMA_INVALID" in _all_codes(ev)


def test_reports_written_and_reproducible(tmp_path: Path) -> None:
    ev = _evaluate("recorded_missing_information_regression")
    first = write_evaluation_reports(tmp_path / "a", ev)
    second = write_evaluation_reports(tmp_path / "b", ev)
    for name in REPORT_FILES:
        a, b = tmp_path / "a" / name, tmp_path / "b" / name
        assert a.exists(), f"missing report {name}"
        assert a.read_bytes() == b.read_bytes(), f"{name} is not reproducible"
    assert set(first) and set(second)
