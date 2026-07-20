# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**FIRST CHECKPOINT (Milestones 0–4): ✅ COMPLETE.**
The platform catches a real structured-output regression, explains it with case-level evidence,
and blocks promotion — offline, with no API credentials. **Next: await go-ahead for M5** (CI +
live provider adapters), the first milestone beyond the checkpoint.

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ✅ complete |
| M3 — Parsing, scoring, reporting | ✅ complete |
| M4 — Baseline, gate, CLI, demo | ✅ complete |
| M5 — CI + provider adapters (Claude/GPT/Gemini/HF) | ⬜ not started (next) |
| M6–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv run pytest -q          # 131 passed
python -m uv run ruff check .        # clean
python -m uv run mypy src            # clean (50 source files)
python -m uv run ai-eval demo        # exit 0: PASS -> FAIL -> PASS
```

## M4 deliverables

- **`baselines/`** — `Baseline` manifest snapshotting an approved run's metrics + per-case
  outcomes; explicit `approve_baseline` (CANDIDATE→ACTIVE; re-approval rejected — the top score
  never auto-promotes); `compare_to_baseline` / `compare_snapshots` producing metric deltas,
  newly-failing and recovered cases, failure-code deltas, and **compatibility warnings**.
- **`gates/`** — versioned `GatePolicy` (thresholds in data, not code) + deterministic evaluator
  returning PASS/FAIL/INVALID with per-rule evidence. Rule-level `SKIPPED` distinguishes "no
  baseline supplied, rule not applicable" from "cannot judge". INVALID takes precedence over FAIL.
- **Operational metrics** — `latency_mean/p50/p95_ms` (numpy percentiles over captured
  `latency_ms`) and `cost_per_case_usd` (only with a versioned price table; never estimated).
- **`harness.py`** — the one module spanning all layers: execute → **re-read raw evidence from
  disk** → parse/score/aggregate → report → compare → gate.
- **`cli/`** — Typer `ai-eval`: `dataset validate`, `run`, `compare`, `gate`, `demo`.
  Exit codes **0 PASS / 1 FAIL / 2 INVALID**, verified end to end.
- **`demo.py`** — self-verifying offline story (returns non-zero if PASS→FAIL→PASS doesn't hold);
  ASCII-only output so it renders on a default Windows cp1252 console.
- **`configs/`** — gate policy (spec §21 defaults), 3 eval plans, price-table README.
- **Tests (+27, 131 total)** — gate semantics incl. INVALID-vs-SKIPPED and precedence; baseline
  approval + comparison; shipped configs validated against **both** JSON Schema and runtime model;
  CLI exit-code contract via `CliRunner`; demo end-to-end.

## First-checkpoint exit criteria — all met

Contracts + ontology checked in ✓ · schemas validate examples ✓ · dataset release immutable and
content-addressed ✓ · raw output retained before parsing ✓ · deterministic scorers tested ✓ ·
every assertion produces an explainable result ✓ · metrics expose denominators ✓ · baseline and
candidate can be compared ✓ · gate passes/fails/invalidates correctly ✓ · **an intentionally
degraded target is caught** ✓ · demo works without credentials ✓ · tests pass ✓ · README separates
implemented from planned ✓.

## Known limitations (carried forward)

- 12 seed cases, not 30–50.
- No live model evaluated yet; recorded fixtures only.
- Latency ≈ 0 and cost `null` offline (honest, not faked) — real at M5.
- No case declares an `evidence_reference_valid` assertion, so that metric's denominator is 0 and
  it is deliberately not gated. Adding it is a dataset-v2 task.
- **User action (non-blocking):** drop the 3 source spec docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · uv + Typer · scikit-learn + numpy in
core · 12 seed cases · sprint-by-sprint pause-each · docs domain-grade + Mermaid · ruff strict ·
all GitHub actions operated by repo owner · targets under test: Claude/ChatGPT/Gemini/HF (M5) +
CatBoost/HF classifier (M9).
