"""Render a run evaluation into machine- and human-readable artifacts.

Serialization only — the report generator computes nothing authoritative; it writes what the
scoring and metrics layers already produced. Outputs mirror the run-artifact layout: per-case
JSONL streams, a metric summary in JSON and CSV, a failure inventory, and a Markdown report
whose every aggregate resolves to case-level evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_eval.evaluation import RunEvaluation


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _assertion_rows(evaluation: RunEvaluation) -> list[dict]:
    rows: list[dict] = []
    for score in evaluation.scores:
        for r in score.results:
            row = r.model_dump(mode="json")
            row["case_id"] = score.case_id
            row["case_version"] = score.case_version
            rows.append(row)
    return rows


def _render_failure_md(evaluation: RunEvaluation) -> str:
    s = evaluation.summary
    lines = ["# Failure Report", ""]
    lines.append(f"- Total cases: **{s.total_cases}**")
    lines.append(f"- Cases passed: **{sum(1 for ci in evaluation.inputs if ci.score.passed)}**")
    lines.append(f"- Critical-case failures: **{s.critical_case_failures}**")
    lines.append(f"- Failing/errored assertions: **{len(evaluation.failures)}**")
    lines.append("")

    counts: dict[str, int] = {}
    for f in evaluation.failures:
        for code in f.failure_codes:
            counts[code] = counts.get(code, 0) + 1
    if counts:
        lines += ["## Failure codes", ""]
        for code, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{code}`: {n}")
        lines.append("")

    if evaluation.failures:
        lines += ["## Failing assertions (most severe first)", ""]
        for f in evaluation.failures:
            sev = f.severity or "n/a"
            codes = ", ".join(f"`{c}`" for c in f.failure_codes) or "—"
            lines.append(f"### {f.case_id} · {f.assertion_id} ({sev})")
            lines.append(f"- scorer: `{f.scorer_ref}` · status: `{f.status}` · codes: {codes}")
            lines.append(f"- expected: `{f.expected}` · observed: `{f.observed}`")
            if f.evidence:
                lines.append(f"- evidence: `{json.dumps(f.evidence, ensure_ascii=False)}`")
            lines.append("")
    else:
        lines += ["_No failing assertions._", ""]
    return "\n".join(lines)


def write_evaluation_reports(run_dir: Path, evaluation: RunEvaluation) -> dict[str, Path]:
    """Write all report artifacts under ``run_dir`` and return the paths by name."""
    run_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["parsed_outputs"] = run_dir / "parsed_outputs.jsonl"
    _write_jsonl(paths["parsed_outputs"], evaluation.parsed)

    paths["assertion_results"] = run_dir / "assertion_results.jsonl"
    _write_jsonl(paths["assertion_results"], _assertion_rows(evaluation))

    paths["metric_summary_json"] = run_dir / "metric_summary.json"
    _write_json(paths["metric_summary_json"], evaluation.summary.model_dump(mode="json"))

    paths["metric_summary_csv"] = run_dir / "metric_summary.csv"
    frame = pd.DataFrame([m.model_dump() for m in evaluation.summary.metrics])
    frame.to_csv(paths["metric_summary_csv"], index=False)

    paths["failures"] = run_dir / "failures.jsonl"
    _write_jsonl(paths["failures"], [f.model_dump(mode="json") for f in evaluation.failures])

    paths["failure_report"] = run_dir / "failure_report.md"
    paths["failure_report"].write_text(_render_failure_md(evaluation), encoding="utf-8")

    return paths
