"""Runtime configuration, read from the environment.

Deliberately dependency-free (no pydantic-settings): a handful of env vars with safe local
defaults. The default database is a local SQLite file, so the API and persistence layer run
from a clean checkout with **no PostgreSQL and no Redis**. Point ``DATABASE_URL`` at Postgres
for the service deployment; point it at ``sqlite:///:memory:`` in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str | None
    runs_dir: str
    execution_mode: str  # "sync" | "celery"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./ai_eval.db"),
        redis_url=os.environ.get("REDIS_URL"),
        runs_dir=os.environ.get("AI_EVAL_RUNS_DIR", "runs"),
        execution_mode=os.environ.get("AI_EVAL_EXECUTION_MODE", "sync"),
    )
