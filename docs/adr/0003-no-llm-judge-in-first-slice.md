# ADR 0003 — No LLM-as-judge in the first slice

- **Status:** Accepted
- **Date:** 2026-07-17

## Context

An LLM judge is easy to reach for and easy to misuse. For exact dates, schema validity, known
labels, set membership, and evidence-reference existence, deterministic code is correct,
cheaper, faster, and reproducible. A judge introduces its own calibration, versioning, and
failure surface.

## Decision

The first slice (M0–M4) uses **only deterministic scorers**. The `semantic_equivalence_judge`
assertion type exists in the contract but is not wired to any case. Grounding is operationalized
through deterministic checks (valid-evidence-reference rate, evidence coverage,
unsupported-material-claim count, contradiction checks) — **not** a vibes-based
`hallucination_score`.

When a judge is later introduced, it must: use a versioned rubric + schema; record model/config;
receive only rubric-required context; store raw output as evidence; keep parse failures visible;
never override a deterministic failure; be calibrated against a human-reviewed sample before
gating.

## Consequences

- The first proof rests on reproducible, explainable scores.
- No model call is required to run the demo or CI gate.
- Judge machinery is deferred until a metric genuinely needs semantic comparison (M3+/M7).
