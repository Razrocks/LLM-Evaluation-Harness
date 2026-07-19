"""Freeze the reference request-triage dataset release.

Loads the reviewable per-case JSON files, validates them (approval required), computes content
hashes, and writes the canonical frozen artifacts:

* ``cases.jsonl``   — finalized cases (each with its ``content_hash``), one per line
* ``manifest.json`` — the immutable, content-addressed :class:`DatasetRelease`

Run: ``python -m uv run python scripts/build_request_triage_release.py``
"""

from __future__ import annotations

from pathlib import Path

from ai_eval.datasets import (
    build_release,
    dump_cases_jsonl,
    finalize_case_hashes,
    load_cases_dir,
    write_manifest,
)

WORKFLOW = "reference.request_triage.v1"
DATASET_ID = "reference.request_triage.dataset"
RELEASE_ID = "reference.request_triage.dataset.v1"
ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "datasets" / "reference" / "request_triage" / "v1"


def main() -> None:
    cases = load_cases_dir(V1 / "cases")
    release = build_release(
        release_id=RELEASE_ID,
        dataset_id=DATASET_ID,
        workflow_ref=WORKFLOW,
        cases=cases,
        purpose="First-checkpoint reference dataset for reference.request_triage.v1.",
        distribution="synthetic, public-safe",
        limitations=[
            "Synthetic scenarios authored for evaluation, not sampled from production traffic.",
            "English-only; single reference timezone family (America/Toronto).",
            "12 seed cases; expansion toward 30-50 is planned.",
        ],
        require_approved=True,
    )
    dump_cases_jsonl(finalize_case_hashes(cases), V1 / "cases.jsonl")
    write_manifest(release, V1 / "manifest.json")
    print(f"Froze {RELEASE_ID}: {len(release.cases)} cases")
    print(f"release content_hash: {release.content_hash}")


if __name__ == "__main__":
    main()
