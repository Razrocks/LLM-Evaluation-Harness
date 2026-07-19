"""Execution contract tests: plan resolution, integrity, and raw-before-parse orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_eval.datasets import (
    build_release,
    dump_cases_jsonl,
    finalize_case_hashes,
    load_cases_dir,
    write_manifest,
)
from ai_eval.execution import (
    EvalPlan,
    PlanResolutionError,
    TargetSpec,
    execute_plan,
    resolve_eval_plan,
)
from ai_eval.targets import get_recorded_target

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = "reference.request_triage.v1"
MANIFEST = "datasets/reference/request_triage/v1/manifest.json"
CASES_DIR = REPO / "datasets" / "reference" / "request_triage" / "v1" / "cases"


def _clock() -> datetime:
    return datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)


def _plan(adapter_id: str = "recorded_pass") -> EvalPlan:
    return EvalPlan(
        eval_plan_id="p",
        workflow_ref=WORKFLOW,
        dataset_manifest_path=MANIFEST,
        target=TargetSpec(adapter_id=adapter_id, adapter_version="v1"),
    )


def test_resolve_pins_all_references() -> None:
    resolved = resolve_eval_plan(_plan(), run_id="run_x", repo_root=REPO, now=_clock())
    manifest = resolved.manifest
    assert len(resolved.cases) == 12
    assert len(manifest.case_refs) == 12
    on_disk = json.loads((REPO / MANIFEST).read_text(encoding="utf-8"))
    assert manifest.dataset_release_hash == on_disk["content_hash"]
    assert manifest.eval_plan_hash.startswith("sha256:")
    assert manifest.output_schema_hash.startswith("sha256:")


def test_workflow_mismatch_raises() -> None:
    plan = _plan().model_copy(update={"workflow_ref": "other.workflow.v1"})
    with pytest.raises(PlanResolutionError):
        resolve_eval_plan(plan, run_id="r", repo_root=REPO, now=_clock())


def test_integrity_detects_tampered_case(tmp_path: Path) -> None:
    cases = load_cases_dir(CASES_DIR)[:2]
    release = build_release(
        release_id="t.v1", dataset_id="t", workflow_ref=WORKFLOW, cases=cases
    )
    ds = tmp_path / "ds"
    ds.mkdir()
    write_manifest(release, ds / "manifest.json")
    # Freeze the manifest against the original cases, then write a TAMPERED cases.jsonl.
    tampered = [cases[0].model_copy(update={"title": "TAMPERED", "content_hash": None}), *cases[1:]]
    dump_cases_jsonl(finalize_case_hashes(tampered), ds / "cases.jsonl")

    plan = EvalPlan(
        eval_plan_id="p",
        workflow_ref=WORKFLOW,
        dataset_manifest_path=str(ds / "manifest.json"),
        target=TargetSpec(adapter_id="recorded_pass", adapter_version="v1"),
    )
    with pytest.raises(PlanResolutionError):
        resolve_eval_plan(plan, run_id="r", repo_root=REPO, now=_clock())


def test_execute_plan_captures_raw_before_parse(tmp_path: Path) -> None:
    result = execute_plan(
        _plan(),
        get_recorded_target("recorded_pass"),
        repo_root=REPO,
        runs_dir=tmp_path,
        run_id="run_t",
        clock=_clock,
    )
    assert str(result.manifest.status) == "completed"
    assert len(result.records) == 12
    assert all(r.state == "response_received" for r in result.records)

    raw_files = list((result.run_dir / "raw").glob("*.json"))
    assert len(raw_files) == 12
    # In M2 there is no parsing step yet; parsed outputs must not exist.
    assert not (result.run_dir / "parsed_outputs.jsonl").exists()
    for record in result.records:
        assert (result.run_dir / record.raw_path).exists()

    manifest = json.loads((result.run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert len(manifest["case_refs"]) == 12


def test_invocation_error_marks_state(tmp_path: Path) -> None:
    result = execute_plan(
        _plan("recorded_schema_failure"),
        get_recorded_target("recorded_schema_failure"),
        repo_root=REPO,
        runs_dir=tmp_path,
        run_id="run_sf",
        clock=_clock,
    )
    # schema_failure still returns raw output (a schema-invalid body); M2 only captures it, so
    # the case-execution state is response_received. The schema failure is detected in M3.
    assert all(r.state == "response_received" for r in result.records)
    assert len(list((result.run_dir / "raw").glob("*.json"))) == 12
