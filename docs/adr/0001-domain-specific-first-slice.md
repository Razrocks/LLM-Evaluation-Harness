# ADR 0001 — A domain-specific first slice, not a generic platform

- **Status:** Accepted
- **Date:** 2026-07-17

## Context

Generic "evaluate anything" LLM platforms tend to produce excessive configuration, weak
semantics, and a polished dashboard reporting metrics nobody validated. The spec is emphatic:
prove one concrete workload before widening.

## Decision

Build `reference.request_triage.v1` as a complete vertical slice (M0–M4) — strict output
validation, deterministic deadline/risk/missing-information scoring, evidence checks, reports,
baseline comparison, and a regression gate — **before** adding any second workload, provider
matrix, persistence, vector store, or dashboard. Do not widen until M4 is green.

## Consequences

- Contracts (schemas, assertions, scorers, gates) are validated against a real workload early.
- Later workloads (RAG, governed tool-use, classification) reuse the same contracts rather than
  inventing parallel ones.
- The repository is useful and demoable at M4 with zero external dependencies.
