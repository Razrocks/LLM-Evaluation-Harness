# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-17**.

## Current position

**Sprint 0 (Milestone 0 — Specification Lock): ✅ complete.**
Cadence: sprint-by-sprint, pause after each milestone. First checkpoint = M0–M4 (offline, no
API keys). Do not widen until M4 is green. **Next: await go-ahead for M1.**

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock (docs + schemas) | ✅ complete |
| M1 — Dataset & domain core | ⬜ not started (next) |
| M2 — Execution & evidence capture | ⬜ not started |
| M3 — Parsing, scoring, reporting | ⬜ not started |
| M4 — Baseline, gate, CLI, demo | ⬜ not started |
| M5–M10 + external adapters | ⬜ roadmap only |

## Sprint 0 deliverables (all verified)

- **Scaffold** — `pyproject.toml` (uv/PEP621, dep groups core/providers/rag/ml/api/worker + dev),
  `.gitignore`, `.env.example`, `README.md`, `src/ai_eval/` package + `py.typed`. `uv sync` clean
  (pydantic 2.13, typer, jsonschema, numpy, pandas, scikit-learn, pytest, ruff, mypy). Runner =
  `python -m uv run`.
- **Schemas (8)** — `schemas/`: `eval_case.v1`, `assertion.v1`, `run_manifest.v1`,
  `assertion_result.v1`, `gate_policy.v1` + `reference/`: `request_triage_input.v1`,
  `request_triage_output.v1`, `trace_event.v1`. Draft 2020-12.
- **Examples (8)** — `schemas/examples/*.example.json`, one per schema, cross-`$ref` resolved.
- **Schema test** — `tests/unit/test_schemas.py`: **17 passed** (8 meta-validation + 8 example
  validation + 1 coverage). `ruff check .` clean; `mypy src` clean.
- **Docs (domain/onboarding-grade, with Mermaid diagrams)** — `docs/`: architecture (system
  context, pipeline sequence, component, ER, state machines, det/agentic, storage), project-thesis,
  system-boundary, business-ontology (app + roles + use cases + worked example + per-entity depth +
  banned terms + edge cases), engineering-ontology, deterministic-agentic-boundary, memory-model,
  integration-boundaries, failure-taxonomy, workflow-contracts/reference-request-triage-v1.
- **ADRs (4)** — 0001 domain-first, 0002 raw-before-parse, 0003 no-judge-first-slice,
  0004 qdrant-derived-index.
- **Tech + roadmap** — `technology-map.md` (anti-checkbox table) + `roadmap/` phases 5–10 +
  external-adapters. `docs/spec/README.md` manifest.

## Notes / corrections

- A duplicate, versioned example set (`*.v1.example.json`, incl. a `reference/` subdir) was
  mistakenly added during the doc pass and has been **removed**; the canonical examples are the
  original flat `schemas/examples/<concept>.example.json` set (richer — e.g. `eval_case` carries 6
  assertions). `test_schemas.py` maps example→schema by version-agnostic concept stem.
- **User action (non-blocking):** drop the 3 verbatim source docs (`01_…md`, `02_…md`,
  `03_master_build_prompt.md`) into `docs/spec/` per its README.

## Verification commands

```bash
python -m uv sync
python -m uv run pytest -q          # 17 passed
python -m uv run ruff check .       # clean
python -m uv run mypy src           # clean
```

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · **uv + Typer** · **scikit-learn +
numpy in core** · **12 seed cases when M1 lands** (expand to 30–50 later) · sprint-by-sprint
pause-each · docs are domain-grade + Mermaid diagrams · all GitHub actions operated by repo owner ·
targets under test: Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF classifier (M9).
