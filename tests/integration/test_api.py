"""API integration tests — full round-trips through the real FastAPI app on in-memory SQLite.

No PostgreSQL, no Redis, no network. Skipped entirely if the optional ``api`` extra is not
installed, so the offline core test run is unaffected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from ai_eval.api import create_app  # noqa: E402
from ai_eval.service import ApplicationService  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PLAN = json.loads((REPO / "configs/plans/reference_request_triage_baseline.json").read_text())
DEGRADED = json.loads(
    (REPO / "configs/plans/reference_request_triage_candidate_degraded.json").read_text()
)
GATE = json.loads((REPO / "configs/gates/reference_request_triage_v1.json").read_text())

OPERATOR = {"X-Role": "eval_operator", "X-Actor-Id": "alice"}
READONLY = {"X-Role": "read_only_stakeholder", "X-Actor-Id": "bob"}
APPROVER = {"X-Role": "baseline_approver", "X-Actor-Id": "carol"}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    service = ApplicationService(
        database_url="sqlite:///:memory:", repo_root=REPO, runs_dir=tmp_path / "runs"
    )
    return TestClient(create_app(service))


def _create(client: TestClient, plan: dict, run_id: str, headers: dict) -> object:
    return client.post(
        "/eval-runs", json={"plan": plan, "gate_policy": GATE, "run_id": run_id}, headers=headers
    )


def test_health_and_capabilities(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    caps = client.get("/capabilities").json()
    assert "reference.request_triage.v1" in caps["workflows"]
    assert "recorded_pass" in caps["recorded_targets"]
    assert "anthropic" in caps["providers"]


def test_unknown_role_is_rejected(client: TestClient) -> None:
    resp = _create(client, PLAN, "r", {"X-Role": "wizard", "X-Actor-Id": "x"})
    assert resp.status_code == 400


def test_read_only_cannot_execute_run(client: TestClient) -> None:
    assert _create(client, PLAN, "r1", READONLY).status_code == 403


def test_operator_run_persisted_and_retrievable(client: TestClient) -> None:
    resp = _create(client, PLAN, "run_ok", OPERATOR)
    assert resp.status_code == 200
    body = resp.json()
    assert body["gate_outcome"] == "pass"
    assert body["cases_passed"] == 12

    detail = client.get("/eval-runs/run_ok").json()
    assert detail["run_id"] == "run_ok"
    assert detail["metric_summary"]["total_cases"] == 12

    results = client.get("/eval-runs/run_ok/results").json()
    assert results["gate_result"]["outcome"] == "pass"

    assert len(client.get("/eval-runs").json()) == 1


def test_degraded_run_records_fail_gate(client: TestClient) -> None:
    body = _create(client, DEGRADED, "run_bad", OPERATOR).json()
    assert body["gate_outcome"] == "fail"
    assert body["critical_case_failures"] > 0
    results = client.get("/eval-runs/run_bad/results").json()
    codes = {c for f in results["failures"] for c in f["failure_codes"]}
    assert "MISSING_INFO_OMITTED" in codes


def test_missing_run_is_404(client: TestClient) -> None:
    assert client.get("/eval-runs/nope").status_code == 404


def test_baseline_approval_is_role_gated_and_audited(client: TestClient) -> None:
    _create(client, PLAN, "run_base", OPERATOR)
    payload = {"baseline_id": "b1", "run_id": "run_base", "rationale": "reference config"}

    assert client.post("/baselines", json=payload, headers=OPERATOR).status_code == 403

    approved = client.post("/baselines", json=payload, headers=APPROVER)
    assert approved.status_code == 200
    assert approved.json()["state"] == "active"
    assert approved.json()["approved_by"] == "carol"

    audit = client.get("/audit/b1").json()
    assert [e["action"] for e in audit] == ["baseline.approved"]
    assert audit[0]["role"] == "baseline_approver"


def test_run_publish_is_idempotent(client: TestClient) -> None:
    _create(client, PLAN, "dup", OPERATOR)
    _create(client, PLAN, "dup", OPERATOR)
    assert len(client.get("/eval-runs").json()) == 1


def test_gate_endpoint_on_stored_run(client: TestClient) -> None:
    _create(client, PLAN, "gated", OPERATOR)
    resp = client.post(
        "/gates/evaluate", json={"run_id": "gated", "policy": GATE}, headers=OPERATOR
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "pass"
