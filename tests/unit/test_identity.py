"""Authorization matrix: who may execute runs, approve baselines, and evaluate gates."""

from __future__ import annotations

import pytest

from ai_eval.identity import Action, PermissionDenied, Principal, Role, authorize


@pytest.mark.parametrize("role", list(Role))
def test_everyone_can_view(role: Role) -> None:
    authorize(Principal(actor_id="x", role=role), Action.VIEW)  # no raise


def test_only_privileged_roles_execute_runs() -> None:
    for role in (Role.EVAL_OPERATOR, Role.RELIABILITY_MAINTAINER, Role.BASELINE_APPROVER,
                 Role.SYSTEM_PRINCIPAL):
        authorize(Principal(actor_id="x", role=role), Action.EXECUTE_RUN)
    for role in (Role.EVAL_AUTHOR, Role.DOMAIN_REVIEWER, Role.READ_ONLY_STAKEHOLDER):
        with pytest.raises(PermissionDenied):
            authorize(Principal(actor_id="x", role=role), Action.EXECUTE_RUN)


def test_only_baseline_approver_approves_baseline() -> None:
    authorize(Principal(actor_id="x", role=Role.BASELINE_APPROVER), Action.APPROVE_BASELINE)
    for role in (Role.EVAL_OPERATOR, Role.RELIABILITY_MAINTAINER, Role.SYSTEM_PRINCIPAL,
                 Role.READ_ONLY_STAKEHOLDER):
        with pytest.raises(PermissionDenied):
            authorize(Principal(actor_id="x", role=role), Action.APPROVE_BASELINE)


def test_permission_denied_names_role_and_action() -> None:
    principal = Principal(actor_id="bob", role=Role.READ_ONLY_STAKEHOLDER)
    with pytest.raises(PermissionDenied) as excinfo:
        authorize(principal, Action.EXECUTE_RUN)
    assert excinfo.value.action is Action.EXECUTE_RUN
    assert "read_only_stakeholder" in str(excinfo.value)
