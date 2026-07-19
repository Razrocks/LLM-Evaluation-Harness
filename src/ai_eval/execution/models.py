"""Execution-side contracts: the plan you ask to run, and the immutable manifest that results.

An :class:`EvalPlan` is the human/CLI-facing request (which workflow, which release, which
target, which scoring plan/gate). The resolver turns it into a :class:`RunManifest` in which
every reference is pinned to an exact version and content hash — a publishable run may contain
no floating references.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import RunStatus


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TargetSpec(_Base):
    adapter_id: str
    adapter_version: str
    output_schema_id: str = "request_triage.output.v1"
    config_refs: dict[str, Any] = Field(default_factory=dict)


class EvalPlan(_Base):
    """The request to run: resolved into a :class:`RunManifest` before execution."""

    eval_plan_id: str
    workflow_ref: str
    dataset_manifest_path: str
    target: TargetSpec
    scoring_plan_id: str = "reference_request_triage_scoring"
    gate_id: str | None = None
    baseline_id: str | None = None


class TargetAdapterRef(_Base):
    adapter_id: str
    adapter_version: str
    config_refs: dict[str, Any] = Field(default_factory=dict)


class ManifestCaseRef(_Base):
    """Case pointer inside a run manifest (id + version only, per run_manifest.v1)."""

    case_id: str
    case_version: int = Field(ge=1)


class RunManifest(_Base):
    """Content-addressed snapshot of every resolved input needed to reproduce a run.

    The ``model_config`` JSON key is exposed via the ``model_configuration`` field alias because
    ``model_config`` is reserved by Pydantic. Always serialize with ``by_alias=True``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str
    repo_revision: str | None = None
    eval_plan_id: str
    eval_plan_hash: str
    workflow_ref: str
    dataset_release_id: str
    dataset_release_hash: str
    case_refs: list[ManifestCaseRef]
    target_adapter: TargetAdapterRef
    prompt_spec_id: str | None = None
    prompt_spec_hash: str | None = None
    model_configuration: dict[str, Any] | None = Field(default=None, alias="model_config")
    output_schema_id: str
    output_schema_hash: str
    retrieval_config_id: str | None = None
    retrieval_config_hash: str | None = None
    scoring_plan_id: str
    scoring_plan_hash: str
    scorer_versions: dict[str, str] = Field(default_factory=dict)
    gate_id: str | None = None
    gate_hash: str | None = None
    baseline_id: str | None = None
    baseline_run_id: str | None = None
    price_table_id: str | None = None
    price_table_hash: str | None = None
    random_seed: int | None = None
    timeout_retry_config: dict[str, Any] | None = None
    environment: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None
    status: RunStatus = RunStatus.CREATED

    def as_json(self) -> dict[str, Any]:
        """Serialize to the on-disk manifest shape (with the ``model_config`` alias)."""
        return self.model_dump(mode="json", by_alias=True)
