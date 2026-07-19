# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**Sprint 3 (Milestone 3 — Parsing, scoring, reporting): ✅ complete.**
Cadence: sprint-by-sprint, pause after each milestone. First checkpoint = M0–M4 (offline, no
API keys). Do not widen until M4 is green. **Next: await go-ahead for M4 (baseline, gate, CLI,
demo) — the last milestone of the first checkpoint.**

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ✅ complete |
| M3 — Parsing, scoring, reporting | ✅ complete |
| M4 — Baseline, gate, CLI, demo | ⬜ not started (next) |
| M5–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv run pytest -q          # 104 passed
python -m uv run ruff check .        # clean
python -m uv run mypy src            # clean (40 source files)
```

## M3 deliverables

- **`parsing/`** — `TriageOutput` Pydantic model (`request_triage.output.v1`, required fields have
  no defaults) + strict `parse_triage_output` keeping empty / malformed-JSON / schema-invalid
  **distinct** (ADR 0002), no silent repair.
- **`scoring/`** — versioned deadline normalizer (`normalize_iso_date` + `resolve_relative_weekday`,
  no wall-clock, boundary-tested); tiny deterministic selector resolver; `AssertionResult`;
  missing-info canonical vocab + versioned alias map; **11 scorers + registry** (schema_valid,
  normalized_date_equal, deadline_kind_equal, categorical_equal [risk under/over], boolean_equal,
  set_precision_recall_f1, required_task_coverage, evidence_reference_valid, evidence_span_support,
  unsupported_material_claim_absent, prohibited_value_absent); `evaluate_case` guarantees one
  result per assertion (unknown scorer → `SCORER_ERROR`).
- **`evidence/`** — `EvidenceIndex` (reference validity, span-bounds, deterministic containment
  support).
- **`metrics/`** — aggregator with explicit numerator/denominator/missing-data per metric;
  **scikit-learn** for risk macro-F1 + confusion matrix; invocation errors excluded from quality
  numerators.
- **`failures/`** — controlled failure inventory (`FailureRecord`, severity-ordered, code counts).
- **`evaluation/`** — `evaluate_raw_outputs` pipeline (parse → score → aggregate → failures).
- **`reporting/`** — JSONL/JSON/CSV(pandas)/Markdown writers; byte-for-byte reproducible.
- **Tests (104 total)** — parser distinctions; normalizer boundaries (week/month/year, tz);
  every scorer pass+fail + invariant #8 + SCORER_ERROR; metric hand-calc **cross-checked against
  scikit-learn**; golden run of all 5 recorded targets + report reproducibility.

## Verified behaviors (the core proof, working)

recorded_pass → 100% pass, 0 critical failures. missing-information regression → schema_pass_rate
**stays 1.0** but missing_information_recall **collapses to 0.0** with `MISSING_INFO_OMITTED` — the
exact "valid JSON, silently worse" regression. deadline/evidence/schema regressions each isolate
their codes; risk metrics report **None** (not 0) when nothing parses.

## Deferred to M4 (next)

Baseline manifest + comparison; deterministic gate evaluator (PASS/FAIL/INVALID + exit codes)
consuming `gate_policy.v1`; Typer CLI (`dataset`/`run`/`compare`/`gate`/`demo`); wiring the
M2 orchestrator raw-capture → M3 evaluation → reports into one run; offline regression demo
(PASS → FAIL → PASS).

## Notes

- Ruff strict (spec §3.5.1). **User action (non-blocking):** drop the 3 source docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · **uv + Typer** · **scikit-learn +
numpy in core** · 12 seed cases (expand to 30–50 later) · sprint-by-sprint pause-each · docs
domain-grade + Mermaid · all GitHub actions operated by repo owner · targets under test:
Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).
