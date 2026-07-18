# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-17**.

## Current position

**Sprint 0 (Milestone 0 — Specification Lock): 🟡 in progress (~80%).**
Cadence: sprint-by-sprint, pause after each milestone. First checkpoint = M0–M4 (offline, no
API keys). Do not widen until M4 is green.

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | 🟡 in progress |
| M1 — Dataset & domain core | ⬜ not started |
| M2 — Execution & evidence capture | ⬜ not started |
| M3 — Parsing, scoring, reporting | ⬜ not started |
| M4 — Baseline, gate, CLI, demo | ⬜ not started |
| M5–M10 + external adapters | ⬜ roadmap only |

## Done in Sprint 0

- **0.1 Scaffold** ✅ — `pyproject.toml` (uv/PEP621, dep groups core/providers/rag/ml/api/worker + dev), `.gitignore`, `.env.example`, `README.md`, `src/ai_eval/` package + `py.typed`. `git init` + remote `origin` (SSH→needs HTTPS for push). uv installed via pip; `uv sync` clean (pydantic 2.13, typer, jsonschema, numpy, pandas, scikit-learn, pytest, ruff, mypy). Runner = `python -m uv run`.
- **0.3 Schemas** ✅ — 8 JSON Schemas under `schemas/` (eval_case, assertion, run_manifest, assertion_result, gate_policy + reference/{request_triage_input, request_triage_output, trace_event}), 8 example payloads, `tests/unit/test_schemas.py` → **17 passed** (meta-valid draft-2020-12 + examples validate + ref resolution).
- **0.4 Docs** ✅ — project-thesis, system-boundary, business-ontology, engineering-ontology, deterministic-agentic-boundary, memory-model, integration-boundaries, failure-taxonomy, workflow-contracts/reference-request-triage-v1.
- **0.5 ADRs** ✅ — 0001 domain-first, 0002 raw-before-parse, 0003 no-judge-first-slice, 0004 qdrant-derived-index.
- **0.6 (partial)** 🟡 — `technology-map.md` done; roadmap `phase-5` done.

## ⚠️ Doc-depth rework required before M0 closes

User feedback (2026-07-17): the current `docs/*.md` are **too thin** — terse tables that
restate the spec. They must be rewritten to **domain/onboarding-grade** depth: narrative, real
use cases, worked end-to-end examples, and each entity explained with definition + why it
exists + example + lifecycle + relationships. **business-ontology.md** especially must describe
the *application and its use cases*, not a glossary. **Decision: rewrite ALL M0 docs in one
pass.** The 0.3 schemas + tests are solid and stay; the 0.4/0.5/0.6 docs written so far are
first drafts to be expanded. Target structure for business-ontology: (1) what the app is,
(2) users/roles, (3) use-case scenarios, (4) worked example, (5) per-entity depth, (6) domain
language + banned terms, (7) edge cases/ambiguity.

## Remaining in Sprint 0 (resume here tomorrow — do #1 FIRST)

1. **Rewrite all M0 docs to domain/onboarding-grade depth** (thesis, system-boundary,
   business-ontology, engineering-ontology, deterministic-agentic-boundary, memory-model,
   integration-boundaries, failure-taxonomy, workflow-contract) **with Mermaid diagrams** —
   plus a new `docs/architecture.md`. Core diagram set: system architecture (components +
   boundaries), eval pipeline / run-lifecycle sequence, entity-relationship map, and the
   state machines (case / dataset release / run / case execution / baseline). Mermaid fenced
   blocks (GitHub-native). Heavier diagrams may trail later.
2. **0.6** roadmap stubs: `phase-6-persistence-api-workers`, `phase-7-rag-qdrant`,
   `phase-8-governed-tool-use-evals`, `phase-9-ml-baselines`, `phase-10-dashboard-hardening`,
   `external-target-adapters` (also written at real depth).
3. **0.2** `docs/spec/README.md` manifest + user to drop the 3 source spec docs into `docs/spec/`.
4. Run `ruff check` + `mypy src` once (baseline clean), then **close Sprint 0** and pause for
   go-ahead into M1.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · **uv + Typer** · **scikit-learn + numpy in core** · **12 seed cases this pass** (expand to 30–50 later) · sprint-by-sprint pause-each · all GitHub actions operated by repo owner · targets under test: Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).

## Verification commands

```bash
uv sync                                   # or: python -m uv sync
python -m uv run pytest -q                # full suite
python -m uv run ruff check .
python -m uv run mypy src
```
