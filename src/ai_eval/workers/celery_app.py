"""Optional Celery-backed durable execution.

Introduced only when run duration justifies a queue. Celery and Redis are optional extras
(``uv sync --extra worker``); this module import-guards them so importing the package never
requires them. The synchronous path (:class:`ai_eval.workers.jobs.SyncJobRunner`) remains the
default and is what the tests and demo use.

The task deliberately re-derives the service inside the worker process from ``DATABASE_URL``
rather than pickling a live service, and persistence stays idempotent on ``run_id``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_celery_app(redis_url: str) -> Any:  # pragma: no cover - requires the worker extra
    try:
        from celery import Celery
    except ImportError as exc:
        raise RuntimeError(
            "celery is not installed; install the optional extra: uv sync --extra worker"
        ) from exc

    app = Celery("ai_eval", broker=redis_url, backend=redis_url)

    @app.task(name="ai_eval.execute_run", acks_late=True, max_retries=3)  # type: ignore[untyped-decorator]
    def execute_run_task(
        actor_id: str, role: str, plan_json: dict[str, Any],
        gate_policy_json: dict[str, Any] | None = None, run_id: str | None = None,
    ) -> dict[str, Any]:
        import os

        from ai_eval.execution import EvalPlan
        from ai_eval.gates import GatePolicy
        from ai_eval.identity import Principal, Role
        from ai_eval.service import ApplicationService

        service = ApplicationService(
            database_url=os.environ["DATABASE_URL"],
            repo_root=Path(os.environ.get("AI_EVAL_REPO_ROOT", ".")),
            runs_dir=Path(os.environ.get("AI_EVAL_RUNS_DIR", "runs")),
        )
        gate = GatePolicy.model_validate(gate_policy_json) if gate_policy_json else None
        return service.execute_run(
            Principal(actor_id=actor_id, role=Role(role)),
            EvalPlan.model_validate(plan_json),
            gate_policy=gate,
            run_id=run_id,
        )

    return app
