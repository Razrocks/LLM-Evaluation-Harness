# Implementation Status

Updated each sprint. Truth source for what is implemented vs planned. Last update: **2026-07-18**.

## Current position

**Sprint 7 (Milestone 7 — RAG + Qdrant): 🟡 retrieval half complete and live-proven; grounded-answer
generation half remaining.** Deterministic ingestion, chunking, embeddings, vector retrieval, and
retrieval metrics are built and tested offline — and the live Qdrant integration test **ran and
passed against the owner's running Qdrant** (`docker compose up -d qdrant`). Grounded-answer
generation evaluation, grounding/faithfulness metrics, retrieval-vs-generation attribution, and
the RAG demo are not built yet.

## Milestone status

| Milestone | Status |
|---|---|
| M0 — Spec lock | ✅ complete |
| M1 — Dataset & domain core | ✅ complete |
| M2 — Execution & evidence capture | ✅ complete |
| M3 — Parsing, scoring, reporting | ✅ complete |
| M4 — Baseline, gate, CLI, demo | ✅ complete |
| M5 — CI + provider adapters | 🟡 code complete; no live model call / CI run (owner) |
| M6 — Persistence, API, workers | 🟡 code complete; Postgres/Redis unexercised (owner) |
| M7 — RAG + Qdrant | 🟡 retrieval eval complete + Qdrant **live-proven**; generation half remaining |
| M8–M10 + external adapters | ⬜ roadmap only |

## Verification (all green)

```bash
python -m uv sync --extra api --extra rag   # api + rag extras
python -m uv run pytest -q                   # 203 passed (incl. live Qdrant test when up)
python -m uv run ruff check .                 # clean
python -m uv run mypy src                     # clean (82 source files)
python -m uv run ai-eval demo                 # exit 0: PASS -> FAIL -> PASS
```

Note: installing the `rag` extra pulls `deepeval`/`langsmith`, whose pytest plugins hang on
startup; `pyproject.toml` disables them via `-p no:deepeval -p no:langsmith_plugin`.

## M7 deliverables so far (retrieval evaluation)

- **`retrieval/models.py`** — canonical `Corpus`/`DocumentVersion`/`Chunk`/`ChunkManifest`/
  `RetrievalConfig`/`RetrievedChunk`. Qdrant is a derived index; these are the source of truth.
- **`retrieval/chunker.py`** — deterministic chunker; stable resolvable IDs
  (`<doc>:<ver>:chunk-<n>`), char spans, content hashes, content-addressed manifest.
- **`retrieval/embeddings.py`** — `HashingEmbedder` (deterministic, offline, no download) +
  `SentenceTransformerEmbedder` (lazy `all-MiniLM-L6-v2`; adapter tested via injected fake).
- **`retrieval/index.py`** — `InMemoryVectorIndex` (offline) + `QdrantVectorIndex` (lazy client).
  Every payload must carry `chunk_id`/`document_version_id`/`corpus_version_id`/`chunk_hash`/
  `embedding_config_id`.
- **`retrieval/retriever.py`** — indexing + retrieval that **validates payload refs against the
  frozen config**, raising on a wrong/stale index or embedding drift.
- **`retrieval/metrics.py`** — Recall@k, Precision@k, MRR, nDCG, empty-retrieval + duplicate-chunk
  rates; aggregate with per-query drill-down. Deterministic, hand-calc tested.
- **`retrieval/ingest.py`** — txt/md direct; pdf/docx lazy (`pypdf`/`python-docx`).
- **Reference corpus** `corpora/reference/business_docs/v1/` (4 docs) + 3 retrieval cases with
  relevant-chunk labels + graded relevance.
- **Tests (+13, 203 total)** — chunk determinism, metric hand-calc, reference-corpus recall,
  payload-integrity + wrong-corpus/embedding-drift/top-k mutations; **live Qdrant round-trip**
  (skips if Qdrant down; ran + passed here).
- **Docker** — Qdrant service added to `docker-compose.yml`.

## M7 remaining (grounded-answer generation)

`reference.grounded_qa.v1` output schema + workflow contract; a grounded-QA target that answers
from retrieved context (reusing the M5 provider adapter); grounding metrics (faithfulness,
evidence coverage, unsupported-claim, correct abstention); retrieval-vs-generation failure
attribution; ragas/deepeval judge adapters (deps installed); the RAG demo; remaining mutations
(mixed-corpus, relevant-chunk-ignored, invented-fact).

## Owner setup done / pending

- ✅ `docker compose up -d qdrant` — Qdrant running (live test passed).
- ⬜ HuggingFace `all-MiniLM-L6-v2` download — only needed for a *semantic* embedder run; the
  Qdrant adapter is already proven with the deterministic embedder.

## Carried-forward limitations

- 12 triage seed cases; RAG corpus is 4 docs / 3 queries.
- M5 provider adapters: no live API call executed; CI never run.
- M6 Postgres/Redis unexercised (SQLite + sync path only).
- **User action (non-blocking):** drop the 3 source spec docs into `docs/spec/`.

## Confirmed build decisions

Package `ai_eval` (src layout) · Python 3.12 · Pydantic v2 · uv + Typer · custom deterministic
RAG pipeline (no LangChain/LlamaIndex) · SQLite default / Postgres for service · sprint-by-sprint
pause-each · docs domain-grade + Mermaid · ruff strict · all GitHub actions + infra + downloads
operated by repo owner · targets under test: Claude/ChatGPT/Gemini/HF (M5) + CatBoost/HF (M9).
