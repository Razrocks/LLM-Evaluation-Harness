# Technology Map

A technology counts as **implemented** only when repository code, tests, fixtures, commands, and
docs demonstrate its use — with (1) a concrete responsibility, (2) actual code, (3) at least one
test or executable demo path, (4) version/config capture where results depend on it, and (5) no
simpler existing component already doing the job. This is an anti-checkbox contract, not a
resume list.

Legend — **Status:** ✅ implemented · 🟡 in progress · ⬜ planned (declared, not built).

> **What 🟡 means for the provider SDKs (M5):** the adapters are written and contract-tested
> against an injected fake client, and a plan + CI workflow exist — but the SDKs are optional
> extras that are **not installed**, and **no live model call has been made yet**. Under the
> rule above, that is not "implemented". They become ✅ when a live run is executed and its
> artifacts are recorded.

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
| Anthropic SDK (**Claude**) | LLM target under test | M5 | `targets/providers/clients.py` | `test_providers.py` (fake client) | Optional | 🟡 |
| OpenAI SDK (**ChatGPT**) | LLM target under test | M5 | `targets/providers/clients.py` | `test_providers.py` (fake client) | Optional | 🟡 |
| google-genai (**Gemini**) | LLM target under test | M5 | `targets/providers/clients.py` | `test_providers.py` (fake client) | Optional | 🟡 |
| HuggingFace transformers | (a) local LLM target (b) text classifier baseline | M5 / M9 | `targets/providers/clients.py`, `ml/` | `test_providers.py` (fake); classifier eval pending | Optional | 🟡 |
| Versioned prompt registry (stdlib templating) | Content-addressed instructions shared by every model | M5 | `prompts/`, `src/ai_eval/prompts/` | `test_prompts_and_pricing.py` | Required | ✅ |
| Versioned price tables | Cost from recorded usage; never estimated | M5 | `src/ai_eval/pricing/`, `configs/price_tables/` | `test_prompts_and_pricing.py` | Optional | ✅ |
| Repeated trials / variance | Spread across runs of one frozen plan | M5 | `src/ai_eval/trials.py` | `test_trials.py` | Optional | ✅ |
| DeepEval / Ragas | Judge + RAG metric adapters (canonical defs stay ours) | M7 | `retrieval/`, `judges/` | RAG metric tests | Optional | ⬜ |
| sentence-transformers (`all-MiniLM-L6-v2`) | Embeddings (pinned revision) | M7 | `retrieval/` | retrieval fixtures | Optional | ⬜ |
| Qdrant + qdrant-client | Derived vector index | M7 | `retrieval/` | index build/query test | Optional | ⬜ |
| pypdf / python-docx | Corpus ingestion | M7 | `retrieval/` | ingestion test | Optional | ⬜ |
| CatBoost | Tabular risk/attention/escalation baseline | M9 | `ml/` | held-out eval + model card | Optional | ⬜ |
| PyTorch / Datasets / Evaluate | Transformer training runtime + data + metrics | M9 | `ml/` | training/eval test | Optional | ⬜ |
| PEFT / TRL (LoRA) | Optional fine-tuning after a measured failure cluster | M9 | `ml/` | fine-tune gate | Optional | ⬜ |
| SQLAlchemy 2.0 / Alembic | Relational models + migrations (SQLite + Postgres) | M6 | `storage/`, `migrations/` | `test_storage.py` (SQLite) | Optional | ✅ |
| PostgreSQL / psycopg | Canonical relational store for the service | M6 | `storage/`, `docker-compose.yml` | driver installed; **no Postgres run** | Optional | 🟡 |
| FastAPI / Uvicorn | Application API | M6 | `api/` | `test_api.py` (TestClient) | Optional | ✅ |
| Celery / Redis | Durable async jobs (sync fallback is default) | M6 | `workers/` | sync path tested; **Celery not run live** | Optional | 🟡 |
| Next.js / React / shadcn / TanStack / Recharts | Dashboard (reads canonical API; no client-side metrics) | M10 | `web/` | e2e | Optional | ⬜ |
| Docker / Docker Compose | Local Postgres/Qdrant/Redis/API/worker profiles | M6–M10 | `Dockerfile`, `docker-compose.yml` | files written; **not run** | Optional | 🟡 |
| GitHub Actions | Lint/type/test + offline regression gate (operated by repo owner) | M5 | `.github/workflows/ci.yml`, `live-providers.yml` | workflows written; **not yet run** | Optional | 🟡 |

## Fine-tune base model (M9, decision pending at that milestone)

Recommended `Qwen/Qwen2.5-0.5B-Instruct` (strong small instruct, permissive license) over the
spec's TinyLlama/SmolLM defaults. Not selected until a stable measured failure cluster justifies
fine-tuning; exact model + revision recorded in the experiment manifest.
