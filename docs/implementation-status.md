# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**Sprint 5 (Milestone 5 — CI + multi-provider comparison): ✅ code complete, live path unexercised.**
The provider layer, prompt registry, price tables, repeated-trial variance, and CI workflows are
built and tested offline. **No live model call has been made and no CI run has executed** — both
are owner-operated. **Next: await go-ahead for M6** (persistence, API, workers).

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ✅ complete |
| M3 — Parsing, scoring, reporting | ✅ complete |
| M4 — Baseline, gate, CLI, demo | ✅ complete |
| M5 — CI + provider adapters | 🟡 code complete; live run + CI run pending (owner) |
| M6 — Persistence, API, workers | ⬜ not started (next) |
| M7–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv run pytest -q          # 168 passed
python -m uv run ruff check .        # clean
python -m uv run mypy src            # clean (59 source files)
python -m uv run ai-eval demo        # exit 0: PASS -> FAIL -> PASS
```

## M5 deliverables

- **`prompts/`** — versioned, **content-addressed** instruction pair
  (`prompts/reference/request_triage/v1/{system,user}.txt`) plus a dependency-free renderer.
  Documents are sorted so the request hash can't change with input ordering. The same prompt
  hash is pinned in every run manifest, which is what makes a cross-model comparison fair.
- **`targets/providers/`** — `ProviderTargetAdapter` (retry **only** on transient kinds, never on
  a semantic failure; attempts/usage/latency/config captured as evidence) plus four clients:
  **AnthropicClient (Claude), OpenAIClient (ChatGPT), GeminiClient, HuggingFaceClient (local)**.
  SDKs are lazy-imported optional extras, and SDK exceptions are normalized into
  `ProviderErrorKind` → controlled `FailureCode`s without importing SDK exception types.
- **`targets/factory.py`** — one `build_target()` resolving recorded fixtures *and* provider
  targets from a plan, so runner/CLI/CI never branch on target kind. API keys are never read or
  stored by platform code; each SDK reads its own env var.
- **`pricing/`** — versioned `PriceTable` + `cost_for_usage`. Cost is `None` whenever it cannot
  be computed honestly (no table, unknown model, missing tokens) — never estimated. The shipped
  `configs/price_tables/example.v1.json` is explicitly marked PLACEHOLDER, not real pricing.
- **Manifest pinning** — prompt spec id/hash, model config, and price table id/hash now resolve
  into the run manifest (invariant #13).
- **`trials.py`** — repeated-trial execution + per-metric mean/stdev/min/max. Metrics absent from
  any run are excluded rather than silently averaged.
- **`.github/workflows/`** — `ci.yml` (offline: lint, types, tests, dataset validation, demo, and
  the regression gate — **no secrets**) and `live-providers.yml` (`workflow_dispatch` only,
  gated by a protected environment, the only place credentials appear).
- **Tests (+14, 168 total)** — provider contract via injected fake client: evidence capture,
  retry-then-succeed, auth fails fast, `RETRY_EXHAUSTED`, **bad JSON never retried**, prompt sent
  matches the rendered spec, SDK-exception classification; factory resolution + error cases;
  prompt determinism/hashing; cost honesty; trial variance.

## Explicitly NOT done in M5 (owner-operated or deferred)

- **No live provider call has been executed.** SDKs are not installed (`uv sync --extra providers`).
- **No CI run has executed** — workflows are files; the repo owner runs them.
- Multi-configuration side-by-side comparison **report** (comparing two live configs in one
  artifact) is not built; `compare_snapshots` supports it, the reporting surface does not.
- `--trials` is not exposed on the CLI yet; `run_trials()` is library-only.

## Known limitations (carried forward)

- 12 seed cases, not 30–50.
- Latency ≈ 0 and cost `null` for recorded targets (honest, not faked).
- No case declares an `evidence_reference_valid` assertion → that metric's denominator is 0 and
  it is deliberately not gated. Dataset-v2 task.
- **User action (non-blocking):** drop the 3 source spec docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · uv + Typer · scikit-learn + numpy in
core · stdlib prompt templating (no Jinja2 dep) · 12 seed cases · sprint-by-sprint pause-each ·
docs domain-grade + Mermaid · ruff strict · all GitHub actions operated by repo owner · targets
under test: Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).
