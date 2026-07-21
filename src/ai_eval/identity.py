"""Roles, principals, and server-side authorization.

The governance roles from ``docs/business-ontology.md`` §"Who uses it", encoded so the three
high-impact actions — executing a run, approving a baseline, and (later) overriding a gate —
carry distinct authority even when one person holds several roles. Authorization is enforced
here, server-side; a client can never grant itself a capability.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    EVAL_AUTHOR = "eval_author"
    DOMAIN_REVIEWER = "domain_reviewer"
    EVAL_OPERATOR = "eval_operator"
    RELIABILITY_MAINTAINER = "reliability_maintainer"
    BASELINE_APPROVER = "baseline_approver"
    READ_ONLY_STAKEHOLDER = "read_only_stakeholder"
    SYSTEM_PRINCIPAL = "system_principal"


class Action(StrEnum):
    VIEW = "view"
    EXECUTE_RUN = "execute_run"
    APPROVE_BASELINE = "approve_baseline"
    EVALUATE_GATE = "evaluate_gate"


#: Which roles may perform each action. Everyone may VIEW; the rest are scoped.
PERMISSIONS: dict[Action, frozenset[Role]] = {
    Action.VIEW: frozenset(Role),
    Action.EXECUTE_RUN: frozenset(
        {Role.EVAL_OPERATOR, Role.RELIABILITY_MAINTAINER, Role.BASELINE_APPROVER,
         Role.SYSTEM_PRINCIPAL}
    ),
    Action.EVALUATE_GATE: frozenset(
        {Role.EVAL_OPERATOR, Role.RELIABILITY_MAINTAINER, Role.BASELINE_APPROVER,
         Role.SYSTEM_PRINCIPAL}
    ),
    #: Baseline approval is deliberately narrow — the top-scoring run never auto-promotes.
    Action.APPROVE_BASELINE: frozenset({Role.BASELINE_APPROVER}),
}


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: str
    role: Role

    def can(self, action: Action) -> bool:
        return self.role in PERMISSIONS[action]


class PermissionDenied(Exception):
    def __init__(self, principal: Principal, action: Action) -> None:
        super().__init__(f"role '{principal.role}' may not perform '{action}'")
        self.principal = principal
        self.action = action


def authorize(principal: Principal, action: Action) -> None:
    if not principal.can(action):
        raise PermissionDenied(principal, action)
