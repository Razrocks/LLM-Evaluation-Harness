# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**Sprint 2 (Milestone 2 — Execution & evidence capture): ✅ complete.**
Cadence: sprint-by-sprint, pause after each milestone. First checkpoint = M0–M4 (offline, no
API keys). Do not widen until M4 is green. **Next: await go-ahead for M3.**

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ✅ complete |
| M3 — Parsing, scoring, reporting | ⬜ not started (next) |
| M4 — Baseline, gate, CLI, demo | ⬜ not started |
| M5–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv run pytest -q          # 64 passed
python -m uv run ruff check .        # clean
python -m uv run mypy src            # clean (19 source files)
```

## M2 deliverables

- **`src/ai_eval/domain/`** — added `TraceEvent`, `StateTransition` (`from` alias +
  `.of()` factory), `ErrorEnvelope` to `models.py`.
- **`src/ai_eval/targets/`** — `base.py` (`TargetAdapter` ABC, `TargetInvocationResult`,
  `Attempt`, `InvocationContext` — provider-neutral, never scores); `fixture.py` (5 recorded
  fixtures: `recorded_pass`, `recorded_missing_information_regression`,
  `recorded_deadline_regression`, `recorded_evidence_regression`, `recorded_schema_failure`,
  synthesized deterministically from each case's approved answer + a registry).
- **`src/ai_eval/execution/`** — `models.py` (`EvalPlan`, `TargetSpec`, `RunManifest` matching
  `run_manifest.v1`), `resolver.py` (pins all refs → manifest; **verifies case-content
  integrity** — tampered `cases.jsonl` fails resolution), `orchestrator.py` (invoke → **raw
  capture before parse** → trace; injectable clock for deterministic runs).
- **`src/ai_eval/artifacts/`** — `writer.py` (atomic writes; `runs/<run_id>/` →
  `run_manifest.json`, `raw/<cx>.json`, `case_executions.jsonl`, `traces.jsonl`).
- **Tests** — `tests/contract/test_targets.py` + `tests/contract/test_execution.py` (64 total).
  Verified: recorded_pass output schema-valid for all 12 cases; each regression variant's
  isolated defect; envelope shape; plan resolution pins refs; integrity catches tampering;
  workflow mismatch rejected; orchestrator captures 12 raw files with no parsed outputs (ADR
  0002 ordering). Produced `run_manifest.json` validates against `run_manifest.v1`.

## Deferred to their milestone (not built yet)

Parser + `request_triage.output.v1` Pydantic model + scorers + metrics + reports (M3);
baseline/gate/CLI/demo (M4). Provider target adapters (Claude/GPT/Gemini/HF) — M5.

## Notes

- Ruff kept strict (spec §3.5.1); config confirmed by user 2026-07-18.
- **User action (non-blocking):** drop the 3 verbatim source docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · **uv + Typer** · **scikit-learn +
numpy in core** · 12 seed cases (expand to 30–50 later) · sprint-by-sprint pause-each · docs
domain-grade + Mermaid · all GitHub actions operated by repo owner · targets under test:
Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).
