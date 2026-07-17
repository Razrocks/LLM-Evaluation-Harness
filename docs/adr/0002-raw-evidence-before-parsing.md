# ADR 0002 — Capture raw target output before parsing or repair

- **Status:** Accepted
- **Date:** 2026-07-17

## Context

If the harness parses, coerces, or repairs target output before persisting it, the record of
what the target *actually* produced is lost, and invalid output can be silently scored as valid.

## Decision

The orchestrator persists the raw target response (and attempts, usage, latency, errors, trace)
to `runs/<run_id>/raw/` **before** any parsing. Parse failure, schema failure, invocation
failure, scoring error, and assertion failure are distinct outcomes that all survive into
reports. Invalid output is stored as evidence and produces a parse/schema failure — never
silently repaired. A repair experiment, if run, is a **separate** target configuration that
preserves the original failure and reports repair success independently.

## Consequences

- Every score is auditable back to the exact bytes the target returned.
- Contract failures are visible and countable, not masked as quality passes.
- Enforced by invariants #5–#7 and tested (raw-before-parse ordering, M2).
