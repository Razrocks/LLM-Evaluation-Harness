"""Freeze approved cases into an immutable, content-addressed dataset release.

The release hash is computed over the **case membership and content** (each entry's
``case_id`` + ``case_version`` + ``content_hash``) plus the workflow — deliberately *not* over
volatile metadata like timestamps or lifecycle state. So freezing the same approved cases
always yields the same release hash (reproducible), while editing any member case changes it.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from ai_eval.domain import (
    CaseRef,
    DatasetRelease,
    DatasetReleaseState,
    EvalCase,
    canonical_json,
    content_hash,
    sha256_hex,
)

from .validation import validate_dataset


class ReleaseError(Exception):
    """A release could not be frozen because its cases failed validation."""


def compute_case_hash(case: EvalCase) -> str:
    """The ``sha256:`` content hash of a case (excluding its own ``content_hash`` field)."""
    return content_hash(case.model_dump(mode="json"))


def finalize_case_hashes(cases: Sequence[EvalCase]) -> list[EvalCase]:
    """Return copies of ``cases`` with ``content_hash`` set to the computed value."""
    return [case.model_copy(update={"content_hash": compute_case_hash(case)}) for case in cases]


def _release_hash(workflow_ref: str, entries: Sequence[CaseRef]) -> str:
    payload = {
        "workflow_ref": workflow_ref,
        "cases": [e.model_dump(mode="json") for e in entries],
    }
    return f"sha256:{sha256_hex(canonical_json(payload))}"


def build_release(
    *,
    release_id: str,
    dataset_id: str,
    workflow_ref: str,
    cases: Sequence[EvalCase],
    purpose: str | None = None,
    distribution: str | None = None,
    limitations: Sequence[str] = (),
    created_at: datetime | None = None,
    require_approved: bool = True,
) -> DatasetRelease:
    """Validate, hash, and freeze ``cases`` into a :class:`DatasetRelease`.

    Raises :class:`ReleaseError` if validation fails.
    """
    report = validate_dataset(
        list(cases), require_approved=require_approved, workflow_ref=workflow_ref
    )
    if not report.ok:
        raise ReleaseError(f"cannot freeze release '{release_id}':\n{report}")

    hashed = finalize_case_hashes(cases)
    entries = sorted(
        (
            CaseRef(case_id=c.case_id, case_version=c.case_version, content_hash=c.content_hash)
            for c in hashed
        ),
        key=lambda r: (r.case_id, r.case_version),
    )

    release = DatasetRelease(
        release_id=release_id,
        dataset_id=dataset_id,
        workflow_ref=workflow_ref,
        state=DatasetReleaseState.FROZEN,
        cases=entries,
        purpose=purpose,
        distribution=distribution,
        limitations=list(limitations),
        created_at=created_at,
    )
    return release.model_copy(update={"content_hash": _release_hash(workflow_ref, entries)})


def write_manifest(release: DatasetRelease, path: Path) -> None:
    """Write the frozen release manifest as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(release.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
