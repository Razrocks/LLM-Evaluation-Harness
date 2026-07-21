"""The FastAPI application.

Endpoints expose the application service's use cases. The service enforces authorization and
owns all authoritative computation; this layer maps HTTP to service calls and domain exceptions
to status codes. It never computes a metric or a gate outcome itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text

from ai_eval.config import load_settings
from ai_eval.identity import PermissionDenied, Principal
from ai_eval.service import ApplicationService, RunNotFound
from ai_eval.targets import RECORDED_TARGETS
from ai_eval.targets.factory import build_target  # noqa: F401  (keeps provider wiring importable)

from .deps import get_principal, get_service
from .schemas import (
    ApproveBaselineRequest,
    Capabilities,
    CreateRunRequest,
    EvaluateGateRequest,
    HealthResponse,
)

ENDPOINTS = [
    "GET /health", "GET /capabilities",
    "POST /eval-runs", "GET /eval-runs", "GET /eval-runs/{run_id}",
    "GET /eval-runs/{run_id}/results",
    "POST /baselines", "POST /gates/evaluate", "GET /audit/{object_id}",
]


def create_app(service: ApplicationService | None = None) -> FastAPI:
    app = FastAPI(title="ai-eval", version="0.1.0")

    if service is None:  # pragma: no cover - exercised by the real service entrypoint
        settings = load_settings()
        service = ApplicationService(
            database_url=settings.database_url,
            repo_root=Path.cwd(),
            runs_dir=Path(settings.runs_dir),
        )
    app.state.service = service

    @app.exception_handler(PermissionDenied)
    async def _denied(_: Any, exc: PermissionDenied) -> Any:  # noqa: ANN401
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.get("/health", response_model=HealthResponse)
    def health(svc: ApplicationService = Depends(get_service)) -> HealthResponse:
        try:
            with svc._sessions() as session:  # noqa: SLF001 - health probe only
                session.execute(text("SELECT 1"))
            db = "ok"
        except Exception:  # pragma: no cover - only on a broken DB
            db = "error"
        return HealthResponse(status="ok", database=db)

    @app.get("/capabilities", response_model=Capabilities)
    def capabilities() -> Capabilities:
        return Capabilities(
            workflows=["reference.request_triage.v1"],
            recorded_targets=sorted(RECORDED_TARGETS),
            providers=["anthropic", "openai", "google", "huggingface"],
            execution_mode=load_settings().execution_mode,
            endpoints=ENDPOINTS,
        )

    @app.post("/eval-runs")
    def create_run(
        body: CreateRunRequest,
        principal: Principal = Depends(get_principal),
        svc: ApplicationService = Depends(get_service),
    ) -> dict[str, Any]:
        try:
            return svc.execute_run(
                principal, body.plan, gate_policy=body.gate_policy, run_id=body.run_id
            )
        except ValueError as exc:  # target build / plan resolution problems
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/eval-runs")
    def list_runs(
        workflow_ref: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        svc: ApplicationService = Depends(get_service),
    ) -> list[dict[str, Any]]:
        return svc.list_runs(workflow_ref=workflow_ref, limit=limit, offset=offset)

    @app.get("/eval-runs/{run_id}")
    def get_run(run_id: str, svc: ApplicationService = Depends(get_service)) -> dict[str, Any]:
        try:
            return svc.get_run(run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"run '{run_id}' not found") from exc

    @app.get("/eval-runs/{run_id}/results")
    def get_results(
        run_id: str, svc: ApplicationService = Depends(get_service)
    ) -> dict[str, Any]:
        try:
            return svc.get_run_results(run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"run '{run_id}' not found") from exc

    @app.post("/baselines")
    def approve_baseline(
        body: ApproveBaselineRequest,
        principal: Principal = Depends(get_principal),
        svc: ApplicationService = Depends(get_service),
    ) -> dict[str, Any]:
        try:
            return svc.approve_baseline_from_run(
                principal, baseline_id=body.baseline_id, run_id=body.run_id,
                rationale=body.rationale,
            )
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"run '{body.run_id}' not found") from exc

    @app.post("/gates/evaluate")
    def evaluate_gate_endpoint(
        body: EvaluateGateRequest,
        principal: Principal = Depends(get_principal),
        svc: ApplicationService = Depends(get_service),
    ) -> dict[str, Any]:
        try:
            return svc.evaluate_stored_gate(principal, run_id=body.run_id, policy=body.policy)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"run '{body.run_id}' not found") from exc

    @app.get("/audit/{object_id}")
    def get_audit(
        object_id: str, svc: ApplicationService = Depends(get_service)
    ) -> list[dict[str, Any]]:
        return svc.get_audit(object_id)

    return app
