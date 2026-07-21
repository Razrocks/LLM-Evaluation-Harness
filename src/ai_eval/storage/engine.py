"""Database engine and session management.

SQLAlchemy 2.0. The same models run on SQLite (local/tests) and PostgreSQL (service), so this
module only decides *which* engine to build. ``create_all`` is used for SQLite convenience;
PostgreSQL deployments run Alembic migrations instead (see ``migrations/``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ai_eval.config import Settings, load_settings

from .models import Base


def build_engine(settings: Settings | None = None) -> Engine:
    settings = settings or load_settings()
    if not settings.is_sqlite:
        return create_engine(settings.database_url, future=True)
    # SQLite: a bare in-memory URL gives each connection its OWN empty database, so share one
    # connection via StaticPool. Also disable the same-thread check for the API's thread pool.
    kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}, "future": True}
    if ":memory:" in settings.database_url:
        kwargs["poolclass"] = StaticPool
    return create_engine(settings.database_url, **kwargs)


def create_all(engine: Engine) -> None:
    """Create tables. Used for SQLite/local and tests; production uses Alembic."""
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """A transactional session scope: commit on success, roll back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
