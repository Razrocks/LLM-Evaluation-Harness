# System Boundary

## In scope

Defining and versioning eval cases; grouping approved cases into immutable dataset releases;
versioned target-output schemas; atomic assertions and scorer contracts; invoking targets
through typed adapters; recording raw outputs, errors, traces, latency, usage **before**
parsing; parsing and schema validation; deterministic scoring; controlled semantic judges
where justified (not in the first slice); retrieval + grounded-answer evaluation (M7);
agent decision / skill / tool / escalation / policy evaluation (M8); metric aggregation with
explicit denominators; failure classification; baseline comparison; deterministic regression
gates; machine- and human-readable reports; immutable run evidence and audit; later an API
and dashboard.

## Out of scope (first slice, and in some cases permanently)

Generic prompt playground; no-code eval builder; autonomous creation/approval of ground-truth;
production request routing; production business-process execution; automatic policy or
approval/permission changes; arbitrary third-party plugin execution; a vector database where
retrieval is not part of the target workflow; a polished UI before stable contracts;
distributed workers; multi-tenant billing; Kubernetes; fine-tuning before a measured failure
cluster.

## Source-of-truth boundary

**Authoritative** for: evaluation definitions and versions; run evidence; scorer results;
baseline and gate decisions; audit history.

**Not authoritative** for: production identity; production authorization; business records;
customer documents outside the copied/versioned eval corpus; organizational policy outside an
explicitly versioned policy snapshot; live model-provider pricing unless captured as a
versioned price table.

## Target-system boundary

A **target system** is an embedded or external workflow whose behavior is evaluated. The
platform calls it but never silently replaces its business logic. The repo ships embedded
reference targets (recorded fixtures for the first slice; provider-backed and other targets
later). An external target never owns the platform's cases, assertions, metrics, baselines, or
gates.

## Standalone execution guarantee

A clean checkout supports a complete **offline** regression demo. Live provider keys, another
product repo, and production infrastructure are all optional. If unavailable, tests and demos
still pass through deterministic or recorded adapters. Missing provider credentials may disable
live comparisons but must never block tests, the offline demo, report generation, gate
evaluation, RAG fixture evaluation, sandbox agent evaluation, or dashboard exploration over
seeded data.

## First-checkpoint scope (M0–M4)

Workflow `reference.request_triage.v1`: load versioned cases → resolve immutable run manifest →
invoke recorded target → capture raw evidence before parsing → parse + validate against
`request_triage.output.v1` → deterministic evidence-backed scorers → metrics with denominators
→ JSONL/JSON/CSV/Markdown reports → baseline comparison → deterministic gate (PASS/FAIL/INVALID
+ CLI exit codes) → prove the gate catches seeded regressions. No keys, no DB, no vector store,
no UI.
