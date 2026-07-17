# Technology Map

A technology counts as **implemented** only when repository code, tests, fixtures, commands, and
docs demonstrate its use — with (1) a concrete responsibility, (2) actual code, (3) at least one
test or executable demo path, (4) version/config capture where results depend on it, and (5) no
simpler existing component already doing the job. This is an anti-checkbox contract, not a
resume list.

Legend — **Status:** ✅ implemented · 🟡 in progress · ⬜ planned (declared, not built).

| Technology | Exact responsibility | Milestone | Source modules | Tests / demo proving use | Req/Opt | Status |
|---|---|---|---|---|---|---|
| Python 3.12 | Primary language | M0 | all of `src/ai_eval/` | full suite | Required | 🟡 |
| Pydantic v2 | Runtime contracts, strict validation, JSON Schema export | M1 | `domain/` | unit (M1) | Required | ⬜ |
| JSON Schema (draft 2020-12) | Provider-neutral portable contracts | M0 | `schemas/` | `tests/unit/test_schemas.py` | Required | ✅ |
| jsonschema | Machine validation of schemas + payloads | M0 | `tests/`, `datasets/` validator | `test_schemas.py` | Required | ✅ |
| JSONL / JSON / CSV / Markdown | Cases + run artifacts | M1–M3 | `datasets/`, `reporting/` | golden + integration | Required | ⬜ |
| NumPy | Numeric arrays, summary stats | M3 | `metrics/` | metric fixtures | Required | ⬜ |
| scikit-learn | macro-F1, confusion matrix, (later) splits/calibration | M3 | `metrics/` | metric fixtures | Required | ⬜ |
| pandas | Result-table construction, slices, CSV export | M3 | `reporting/` | reporting tests | Required | ⬜ |
| python-dateutil | Robust date/weekday parsing under versioned normalizer | M3 | `scoring/` | normalizer boundary tests | Required | ⬜ |
| Typer | CLI (`dataset validate`/`run`/`compare`/`gate`/`demo`) | M4 | `cli/` | CLI exit-code tests | Required | ⬜ |
| pytest / pytest-cov | Test + coverage | M0 | `tests/` | itself | Required | 🟡 |
| Ruff / mypy | Lint + static types | M0 | repo | CI | Required | 🟡 |
| RapidFuzz | Named conservative fuzzy scorer (thresholded, audited) | M3+ | `scoring/` | fuzzy scorer test | Optional | ⬜ |
| Anthropic SDK (**Claude**) | LLM target under test | M5 | `targets/providers/` | opt-in live smoke | Optional | ⬜ |
| OpenAI SDK (**ChatGPT**) | LLM target under test | M5 | `targets/providers/` | opt-in live smoke | Optional | ⬜ |
| google-genai (**Gemini**) | LLM target under test | M5 | `targets/providers/` | opt-in live smoke | Optional | ⬜ |
| HuggingFace transformers | (a) local LLM target (b) text classifier baseline | M5 / M9 | `targets/`, `ml/` | classifier held-out eval | Optional | ⬜ |
| DeepEval / Ragas | Judge + RAG metric adapters (canonical defs stay ours) | M7 | `retrieval/`, `judges/` | RAG metric tests | Optional | ⬜ |
| sentence-transformers (`all-MiniLM-L6-v2`) | Embeddings (pinned revision) | M7 | `retrieval/` | retrieval fixtures | Optional | ⬜ |
| Qdrant + qdrant-client | Derived vector index | M7 | `retrieval/` | index build/query test | Optional | ⬜ |
| pypdf / python-docx | Corpus ingestion | M7 | `retrieval/` | ingestion test | Optional | ⬜ |
| CatBoost | Tabular risk/attention/escalation baseline | M9 | `ml/` | held-out eval + model card | Optional | ⬜ |
| PyTorch / Datasets / Evaluate | Transformer training runtime + data + metrics | M9 | `ml/` | training/eval test | Optional | ⬜ |
| PEFT / TRL (LoRA) | Optional fine-tuning after a measured failure cluster | M9 | `ml/` | fine-tune gate | Optional | ⬜ |
| PostgreSQL / SQLAlchemy / Alembic | Canonical relational store + migrations | M6 | `storage/`, `api/` | persistence tests | Optional | ⬜ |
| FastAPI / Uvicorn | Application API | M6 | `api/` | contract tests | Optional | ⬜ |
| Celery / Redis | Durable async jobs (sync fallback for local) | M6 | `workers/` | worker tests | Optional | ⬜ |
| Next.js / React / shadcn / TanStack / Recharts | Dashboard (reads canonical API; no client-side metrics) | M10 | `web/` | e2e | Optional | ⬜ |
| Docker / Docker Compose | Local Postgres/Qdrant/Redis/API/worker profiles | M6–M10 | `docker-compose.yml` | compose up | Optional | ⬜ |
| GitHub Actions | Lint/type/test + offline regression gate (operated by repo owner) | M5 | `.github/workflows/` | CI runs | Optional | ⬜ |

## Fine-tune base model (M9, decision pending at that milestone)

Recommended `Qwen/Qwen2.5-0.5B-Instruct` (strong small instruct, permissive license) over the
spec's TinyLlama/SmolLM defaults. Not selected until a stable measured failure cluster justifies
fine-tuning; exact model + revision recorded in the experiment manifest.
