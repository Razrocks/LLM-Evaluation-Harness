"""The demo is self-verifying: it returns 0 only if PASS -> FAIL -> PASS actually held.

This is the first checkpoint's acceptance test in one call — dataset validation, a baseline
run that passes the gate, an approved baseline, a degraded candidate that the gate blocks with
case-level evidence, and a corrected run that passes again. No credentials.
"""

from __future__ import annotations

from pathlib import Path

from ai_eval.demo import run_demo

REPO = Path(__file__).resolve().parents[2]


def test_demo_story_holds(tmp_path: Path) -> None:
    lines: list[str] = []
    code = run_demo(repo_root=REPO, runs_dir=tmp_path, echo=lines.append)
    output = "\n".join(lines)
    assert code == 0, output

    # Assert each expected outcome explicitly rather than relying on the exit code alone.
    assert output.count("GATE: PASS") == 2
    assert "GATE: FAIL" in output
    assert "MISSING_INFO_OMITTED" in output
    assert "STILL VALID JSON" in output

    for run_id in ("demo_baseline", "demo_degraded", "demo_corrected"):
        assert (tmp_path / run_id / "run_manifest.json").exists()
        assert (tmp_path / run_id / "gate_result.json").exists()
    # The degraded run compared against the approved baseline.
    assert (tmp_path / "demo_degraded" / "comparison_report.md").exists()
