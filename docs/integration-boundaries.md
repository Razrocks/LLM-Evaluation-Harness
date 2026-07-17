# Integration Boundaries

Every external system is accessed through a **typed adapter** that translates transport
concerns but cannot redefine domain semantics.

## Target system

- **Input:** workflow ID/version, rendered request, context bundle, execution config, trace context.
- **Output:** raw output, optional parsed-native output, trace events, usage, latency, error envelope, target request ID.
- **Boundary:** the target adapter does not score correctness.

## Model provider (M5)

Provider adapters own: auth transport; request formatting; structured-output mode translation;
token/usage extraction; provider error mapping; provider request IDs; model-revision metadata.
They do **not** own: business prompts; expected outputs; metric definitions; retrying semantic
failures; cost truth without a price-table reference. Adapters exist for **Claude (Anthropic),
ChatGPT (OpenAI), Gemini (Google), and local HuggingFace models** behind one interface.

## Relational store (M6)

System of record for structured metadata and run relationships after persistence is introduced:
identifiers/versions, manifests/hashes, states, references to large artifacts, assertion
results, metrics, review/audit records, baseline/gate relationships. Large raw
documents/responses live in object storage with content-addressed references.

## Object / file store

Stores source documents, raw provider payloads, generated reports, large trace artifacts, model
artifacts, corpus snapshots. Interface supports content-hash verification. **First slice uses
the local filesystem** under `runs/<run_id>/`.

## Qdrant (M7)

Owned by the Qdrant adapter: collection/alias creation, vector upsert, vector search, filter
translation, index health/count checks, deletion by corpus/index version. **Not** owned: canonical
text, document lifecycle, eval labels, result aggregation, authorization policy. Every payload
references `chunk_id`, `document_version_id`, `corpus_version_id`, `chunk_hash`,
`embedding_config_id`, and filter dimensions. Qdrant is a **derived index** — see
[adr/0004-qdrant-is-derived-index.md](adr/0004-qdrant-is-derived-index.md).

## CI (M5)

CI receives repo revision, eval plan reference, minimum-scope credentials, optional changed-file
context; produces run reference, gate result, machine report, human summary, artifact links. CI
may block merge/deploy on a deterministic gate result; it may **not** approve overrides.
**GitHub Actions execution is operated by the repository owner**, not by the harness.

## Identity, secrets, observability

Identities/roles come from an external identity boundary. Secrets load at execution time from
env/secret manager and are never stored in run manifests or reports. Operational logs/traces may
be exported, but the evaluation evidence ledger remains authoritative for eval semantics.

## Data export

Exports include: schema version, run/plan IDs, content hashes, sensitivity/redaction metadata,
generated-at timestamp, producer version.
