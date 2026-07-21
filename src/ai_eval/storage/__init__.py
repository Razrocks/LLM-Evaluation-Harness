"""Relational persistence (M6): SQLAlchemy models, engine, and repositories.

The domain layer never imports anything here; this layer depends on the domain, not the reverse.
"""

from __future__ import annotations

from .engine import build_engine, create_all, make_session_factory, session_scope
from .models import AuditEventRow, Base, BaselineRow, EvalRunRow
from .repositories import AuditRepository, BaselineRepository, RunRepository

__all__ = [
    "AuditEventRow",
    "AuditRepository",
    "Base",
    "BaselineRepository",
    "BaselineRow",
    "EvalRunRow",
    "RunRepository",
    "build_engine",
    "create_all",
    "make_session_factory",
    "session_scope",
]
