"""FastAPI dependencies: the current principal and the application service.

The principal is derived from request headers (``X-Actor-Id`` / ``X-Role``) standing in for a
real identity boundary. Authorization is still enforced server-side by the service — the header
only *claims* a role; the service decides what that role may do.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from ai_eval.identity import Principal, Role
from ai_eval.service import ApplicationService


def get_service(request: Request) -> ApplicationService:
    service = getattr(request.app.state, "service", None)
    if service is None:  # pragma: no cover - misconfiguration guard
        raise HTTPException(status_code=500, detail="application service not configured")
    return service


def get_principal(
    x_actor_id: str = Header(default="anonymous"),
    x_role: str = Header(default=Role.READ_ONLY_STAKEHOLDER.value),
) -> Principal:
    try:
        role = Role(x_role)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"unknown role '{x_role}'; valid roles: {[r.value for r in Role]}",
        ) from exc
    return Principal(actor_id=x_actor_id, role=role)
