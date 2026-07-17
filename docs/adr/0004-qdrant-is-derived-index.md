# ADR 0004 — Qdrant is a derived index, not canonical storage

- **Status:** Accepted (forward-looking; implemented in M7)
- **Date:** 2026-07-17

## Context

Vector databases are often treated as the source of truth for documents and labels, which makes
retrieval non-reproducible and couples evaluation correctness to index state.

## Decision

Qdrant stores **derived** vector representations and retrieval metadata only. Canonical source
documents, chunk manifests, expected evidence, labels, prompts, policies, run results, baseline
and gate decisions live in canonical file/object/relational storage. Every Qdrant point payload
references `chunk_id`, `document_version_id`, `corpus_version_id`, `chunk_hash`,
`embedding_config_id`, and filter dimensions. A collection/alias maps to exactly one
corpus/index configuration; stale or mixed-version indexes are invalid and detected by mutation
tests.

## Consequences

- The index is fully rebuildable from canonical sources.
- Retrieval configurations are frozen and reproducible.
- Introduced only when a retrieval-dependent workload (`reference.grounded_qa.v1`, M7) exists —
  never as architecture garnish.
