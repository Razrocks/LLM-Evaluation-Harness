"""Job execution behind one interface, so local mode needs no queue infrastructure.

``SyncJobRunner`` runs a job in-process and is the default everywhere — tests, the offline
demo, and any environment without Redis. ``CeleryJobRunner`` (optional) submits the same job to
a durable queue. Both call the *same* application-service use case, and both are idempotent
because persistence keys on ``run_id``: a retried job re-publishes the identical run rather than
creating a second one.
"""

from __future__ import annotations

from typing import Any, Protocol

from ai_eval.execution import EvalPlan
from ai_eval.gates import GatePolicy
from ai_eval.identity import Principal
from ai_eval.service import ApplicationService


class JobRunner(Protocol):
    def submit_run(
        self,
        principal: Principal,
        plan: EvalPlan,
        *,
        gate_policy: GatePolicy | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute (or enqueue) one eval run and return its result reference."""
        ...


class SyncJobRunner:
    """Runs the job immediately, in-process. No Redis, no Celery."""

    def __init__(self, service: ApplicationService) -> None:
        self.service = service

    def submit_run(
        self,
        principal: Principal,
        plan: EvalPlan,
        *,
        gate_policy: GatePolicy | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        return self.service.execute_run(
            principal, plan, gate_policy=gate_policy, run_id=run_id
        )
