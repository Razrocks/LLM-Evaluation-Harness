"""Eval-plan resolver: turn an :class:`EvalPlan` into an immutable :class:`RunManifest`.

Resolution pins every reference to an exact version + hash and verifies dataset integrity: each
case loaded from ``cases.jsonl`` must re-hash to the value frozen in the release manifest, or
resolution fails. A run cannot start from a tampered or drifted dataset.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_eval.datasets import compute_case_hash, load_cases_jsonl
from ai_eval.domain import DatasetRelease, EvalCase, RunStatus, content_hash

from .models import EvalPlan, ManifestCaseRef, RunManifest, TargetAdapterRef

# The first slice has one workflow, so its output schema path is known. Later workflows extend
# this map (or a schema registry replaces it).
_OUTPUT_SCHEMA_PATHS: dict[str, str] = {
    "request_triage.output.v1": "schemas/reference/request_triage_output.v1.json",
}


class PlanResolutionError(Exception):
    """A plan could not be resolved (missing/incompatible/tampered reference)."""


@dataclass(frozen=True)
class ResolvedPlan:
    manifest: RunManifest
    release: DatasetRelease
    cases: list[EvalCase]


def _output_schema_hash(repo_root: Path, schema_id: str) -> str:
    rel = _OUTPUT_SCHEMA_PATHS.get(schema_id)
    if rel is None:
        raise PlanResolutionError(f"unknown output schema id '{schema_id}'")
    data = json.loads((repo_root / rel).read_text(encoding="utf-8"))
    return content_hash(data, exclude=())


def resolve_eval_plan(
    plan: EvalPlan,
    *,
    run_id: str,
    repo_root: Path,
    repo_revision: str | None = None,
    now: datetime | None = None,
) -> ResolvedPlan:
    now = now or datetime.now(UTC)

    manifest_path = Path(plan.dataset_manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    if not manifest_path.exists():
        raise PlanResolutionError(f"dataset manifest not found: {manifest_path}")

    release = DatasetRelease.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    if release.workflow_ref != plan.workflow_ref:
        raise PlanResolutionError(
            f"workflow mismatch: plan '{plan.workflow_ref}' vs release '{release.workflow_ref}'"
        )
    if release.content_hash is None:
        raise PlanResolutionError(f"release '{release.release_id}' is not frozen (no content_hash)")

    loaded = load_cases_jsonl(manifest_path.parent / "cases.jsonl")
    by_key = {(c.case_id, c.case_version): c for c in loaded}
    cases: list[EvalCase] = []
    for entry in release.cases:
        key = (entry.case_id, entry.case_version)
        case = by_key.get(key)
        if case is None:
            raise PlanResolutionError(f"release references missing case {key}")
        recomputed = compute_case_hash(case)
        if entry.content_hash is not None and recomputed != entry.content_hash:
            raise PlanResolutionError(
                f"case content-hash mismatch for {key}: {recomputed} != {entry.content_hash}"
            )
        cases.append(case)

    manifest = RunManifest(
        run_id=run_id,
        repo_revision=repo_revision,
        eval_plan_id=plan.eval_plan_id,
        eval_plan_hash=content_hash(plan.model_dump(mode="json")),
        workflow_ref=plan.workflow_ref,
        dataset_release_id=release.release_id,
        dataset_release_hash=release.content_hash,
        case_refs=[ManifestCaseRef(case_id=c.case_id, case_version=c.case_version) for c in cases],
        target_adapter=TargetAdapterRef(
            adapter_id=plan.target.adapter_id,
            adapter_version=plan.target.adapter_version,
            config_refs=plan.target.config_refs,
        ),
        output_schema_id=plan.target.output_schema_id,
        output_schema_hash=_output_schema_hash(repo_root, plan.target.output_schema_id),
        scoring_plan_id=plan.scoring_plan_id,
        scoring_plan_hash=content_hash({"scoring_plan_id": plan.scoring_plan_id}),
        gate_id=plan.gate_id,
        baseline_id=plan.baseline_id,
        environment={"python": sys.version.split()[0], "platform": platform.system().lower()},
        created_at=now,
        status=RunStatus.CREATED,
    )
    return ResolvedPlan(manifest=manifest, release=release, cases=cases)
