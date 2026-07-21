# Phase 6 (M6) — Persistence, API & Workers

**Status:** 🟡 Code complete (2026-07-18); tested on in-memory SQLite. PostgreSQL, Redis, and
Docker are unexercised (owner-operated). See [`../implementation-status.md`](../implementation-status.md).

## Goal

Move from local files to a durable, queryable system of record and expose the platform's use
cases over an API — **without** changing a single domain contract. The CLI and the API resolve
and run the *same* eval plan; persistence is an adapter, not a rewrite.

## Why now (and not earlier)

Files are perfect for proving the contracts (M0–M4) and for CI (M5). Persistence earns its place
only once there are many runs to query, compare, and browse, and once an API has real consumers
(the dashboard, external triggers). Adding a database before the contracts are stable would just
freeze immature schemas.

## Deliverables

- **PostgreSQL** canonical relational store; **SQLAlchemy 2.x** models + repositories;
  **Alembic** migrations; **psycopg** driver.
- **FastAPI** application service with **Pydantic v2** request/response contracts; **Uvicorn**
  local server.
- Artifact/object-store adapter (local filesystem first; content-addressed references).
- A **synchronous in-process executor** for tests and offline demos; **Celery + Redis** for
  durable async runs/ingestion/embedding/report jobs — with the sync path always available when
  Redis is absent.
- Role-aware application services + persisted audit events.

## API capability families

```
/datasets   /corpora   /configurations   /eval-runs   /eval-runs/{id}/results
/comparisons   /failures   /baselines   /gates   /reports
/rag/evaluate   /agents/evaluate   /classifiers   /fine-tune/jobs
```

## Exit criteria

API/ORM/worker types never leak into the domain layer; completed-run evidence stays immutable;
browser/client code is never authoritative for metrics or gates; local mode works with no queue
infrastructure; role permissions are enforced server-side; workers are idempotent and never
double-publish a run.

## New dependencies

`api` group (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg[binary]`) and `worker`
group (`celery`, `redis`). **Docker Compose** brings up PostgreSQL + Redis locally.
