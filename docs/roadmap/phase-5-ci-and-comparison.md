# Phase 5 (M5) — CI & Multi-Configuration Comparison

**Status:** 🟡 Code complete (2026-07-18); live provider run and CI run still pending — both are
owner-operated. See [`../implementation-status.md`](../implementation-status.md) for exactly what
was built versus what remains.

## Goal

Compare multiple resolved execution configurations fairly, add cost/latency accounting, and run
the deterministic gate in CI.

## Deliverables

- Provider-neutral target interface + concrete adapters: **Claude** (Anthropic SDK), **ChatGPT**
  (OpenAI SDK), **Gemini** (google-genai), **HuggingFace** local inference, plus the existing
  recorded fixture adapter (default for tests/CI).
- Prompt/instruction registry with content hashes; model-config versioning.
- Versioned price tables → cost per case / per passing case.
- Repeated-trial mode + variance reports for selected cases.
- GitHub Actions: `ruff` + `mypy` + `pytest` + offline demo + regression gate; opt-in live-provider profile; artifact upload; PR summary. **Actions are operated by the repo owner.**
- Fair-comparison resolver (a model name alone is never a complete configuration).

## Exit criteria

CI blocks on deterministic gate failure without secrets; transient provider failure is
distinguished from quality regression; comparison freezes all material inputs; metric/failure
deltas drill to cases and assertions; no secrets/source content leak into logs.

## New dependencies

`providers` group: `anthropic`, `openai`, `google-genai`, `httpx`. **Requires opt-in API keys**
(never for CI/demo).
