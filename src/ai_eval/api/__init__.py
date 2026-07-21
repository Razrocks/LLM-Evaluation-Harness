"""FastAPI application layer (M6). Consumes application services; never computes authoritative
metrics or gate outcomes."""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
