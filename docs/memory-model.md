# Memory Model

No mystical "agent memory." Explicit state stores with different authority, retention, and
mutation rules.

| Class | Contains | Rules |
|---|---|---|
| **A. Immutable definition** | approved case versions, dataset releases, schemas, prompt/scorer specs, policies, gates, corpus/chunk versions | append-only versions; content-addressed; no in-place mutation after approval/freeze |
| **B. Run-local working state** | queued case IDs, current case state, temp request/response handles, retry counters, in-progress aggregates | scoped to one run; mutable during execution; final state snapshotted into immutable evidence; not business truth |
| **C. Evidence** | raw requests/responses, trace events, provider IDs, source spans, retrieved chunk IDs, usage/latency, parser outputs, scorer inputs/outputs | append-only after capture; redaction/retention policies apply; transformations keep links to originals |
| **D. Analytical** | aggregate metrics, comparisons, failure clusters, reports, trends | always derivable from A + C; records producer/version; may be regenerated; never silently overwrites prior analysis |
| **E. Human decision** | reviews, adjudications, approvals, baseline decisions, gate overrides, rationales | actor + authority required; append-only; supersession explicit; overrides do not erase original outcomes |
| **F. Retrieval index** (M7) | vectors, chunk IDs, filter metadata, embedding/config references | derived and rebuildable; Qdrant is not canonical storage; collection/alias maps to one corpus/index version; stale/mixed-version indexes are invalid |

## Context assembly

Any model-assisted step receives a **declared context bundle** recording: source references;
exact rendered content or content hashes; ordering; truncation; token counts; retrieval config;
prompt spec; redactions. Hidden chat history must not influence a publishable run unless
captured as an explicit versioned input artifact.

## Retention and sensitivity

Supports sensitivity classification; field/artifact-level redaction; secrets exclusion;
configurable retention for raw provider payloads; irreversible deletion only where legally
required (with tombstone audit records); synthetic datasets for public demos.

## First slice (M0–M4)

Only classes **A** (schemas, cases, dataset release, gate policy), **B** (in-process run
state), **C** (raw outputs + assertion results under `runs/<run_id>/`), and **D** (metrics,
comparison, reports) are exercised. All on the local filesystem; no database.
