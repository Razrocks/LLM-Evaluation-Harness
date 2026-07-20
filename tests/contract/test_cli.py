"""CLI exit-code contract — the interface CI depends on.

0 = PASS, 1 = FAIL, 2 = INVALID. These are asserted end to end through the real Typer app.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_eval.cli import app
from ai_eval.gates import EXIT_FAIL, EXIT_PASS

REPO = Path(__file__).resolve().parents[2]
DATASET = "datasets/reference/request_triage/v1"
GATE = "configs/gates/reference_request_triage_v1.json"
BASELINE_PLAN = "configs/plans/reference_request_triage_baseline.json"
DEGRADED_PLAN = "configs/plans/reference_request_triage_candidate_degraded.json"

runner = CliRunner()


def test_dataset_validate_passes() -> None:
    result = runner.invoke(app, ["dataset", "validate", "--dataset", DATASET])
    assert result.exit_code == EXIT_PASS, result.output
    assert "12 case(s) valid" in result.output


def test_run_baseline_gate_passes(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--plan", BASELINE_PLAN, "--gate", GATE,
         "--runs-dir", str(tmp_path), "--run-id", "t_pass"],
    )
    assert result.exit_code == EXIT_PASS, result.output
    assert "GATE: PASS" in result.output
    assert (tmp_path / "t_pass" / "metric_summary.json").exists()
    assert (tmp_path / "t_pass" / "gate_result.json").exists()


def test_run_degraded_gate_fails_with_nonzero_exit(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--plan", DEGRADED_PLAN, "--gate", GATE,
         "--runs-dir", str(tmp_path), "--run-id", "t_fail"],
    )
    assert result.exit_code == EXIT_FAIL, result.output
    assert "GATE: FAIL" in result.output
    assert "missing_information_recall" in result.output


def test_gate_command_on_stored_run(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["run", "--plan", BASELINE_PLAN, "--runs-dir", str(tmp_path), "--run-id", "stored"],
    )
    result = runner.invoke(
        app, ["gate", "--run", str(tmp_path / "stored"), "--policy", GATE]
    )
    assert result.exit_code == EXIT_PASS, result.output
    assert "GATE: PASS" in result.output
