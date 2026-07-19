# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**Sprint 1 (Milestone 1 — Dataset & domain core): ✅ complete.**
Cadence: sprint-by-sprint, pause after each milestone. First checkpoint = M0–M4 (offline, no
API keys). Do not widen until M4 is green. **Next: await go-ahead for M2.**

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ⬜ not started (next) |
| M3 — Parsing, scoring, reporting | ⬜ not started |
| M4 — Baseline, gate, CLI, demo | ⬜ not started |
| M5–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv run pytest -q          # 41 passed
python -m uv run ruff check .        # clean
python -m uv run mypy src            # clean (10 source files)
python -m uv run python scripts/build_request_triage_release.py   # re-freezes the release
```

## M1 deliverables

- **`src/ai_eval/domain/`** — `enums.py` (all controlled vocabularies + lifecycle states as
  `StrEnum`), `models.py` (Pydantic v2, `extra="forbid"`: EvalCase, Assertion, EvidenceUnit,
  EvidenceRequirement, Provenance, Review, Ambiguity, CaseRef, DatasetRelease), `hashing.py`
  (canonical JSON + `sha256:` content hashing), `failure_codes.py` (full taxonomy enum).
- **`src/ai_eval/datasets/`** — `loader.py` (`load_cases_jsonl`, `load_cases_dir`,
  `dump_cases_jsonl`), `validation.py` (per-case + collection checks → typed
  `ValidationReport`), `release.py` (content-addressed freezer, reproducible release hash).
- **Reference dataset** — 12 reviewed seed cases at
  `datasets/reference/request_triage/v1/cases/*.json`; frozen `manifest.json` +
  `cases.jsonl` + `release_notes.md`. Coverage: risk high/med/low = 5/4/3; criticality
  critical 5; deadline kinds relative 4 / none 5 / absolute 2 / ambiguous 1; adversarial cases
  (prompt-injection, unsupported-action, tone-decoupled, doc conflicts).
- **`scripts/build_request_triage_release.py`** — validates + freezes the release.
- **Tests** — `tests/unit/test_domain.py`, `tests/unit/test_datasets.py` (41 total incl. M0
  schema tests): case/dataset validation, missing-selector + duplicate-assertion detection,
  content-hash-mismatch (immutability), duplicate/workflow/approval/empty-dataset checks,
  release hash reproducibility + edit-sensitivity, JSONL round-trip, reference-release
  load/validate, manifest-hash reproducibility.

## Deferred to their milestone (not built yet)

Pydantic models for RunManifest, AssertionResult, ExecutionConfig, ScoringPlan, EvalPlan,
Metric, Baseline, GatePolicy are built in M2–M4 where their logic lands (JSON Schemas for them
already exist under `schemas/`). The `request_triage.output.v1` Pydantic model lands in M3
(parsing).

## Notes / corrections

- A duplicate versioned example set added during M0 was removed; canonical examples are the
  flat `schemas/examples/<concept>.example.json` set. (See git history.)
- **User action (non-blocking):** drop the 3 verbatim source docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · **uv + Typer** · **scikit-learn +
numpy in core** · 12 seed cases (expand to 30–50 later) · sprint-by-sprint pause-each · docs
domain-grade + Mermaid · all GitHub actions operated by repo owner · targets under test:
Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).
