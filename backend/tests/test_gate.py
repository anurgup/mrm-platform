"""
Tests for the deployment gate (app/services/gate.py, app/api/gate.py).

NOTE on risk scores: the spec asked for Model 1 at score 75 and Model 2 at
score 80. Both are unreachable — the risk engine's max achievable score is
70 (established in P-1.1: every rule's points are multiples of 5, and
complexity=20 requires a model_type that's mutually exclusive with the
model_type vendor=20 requires, so they can never both apply). Both models
below score exactly 70 instead — still HIGH tier, via different underlying
rule combinations, which is what the gate actually cares about.
"""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Finding, FindingStatus, Severity
from app.services.regulatory import resolve_reference
from app.services.regulatory_seed import seed_regulatory_mappings
from tests.test_ai_models import make_model_payload


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    seed_regulatory_mappings(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _build_and_assess(client: TestClient, **overrides: Any) -> dict:
    payload = make_model_payload(**overrides)
    model = client.post("/models", json=payload).json()
    client.post(f"/models/{model['id']}/assess")
    client.post(f"/models/{model['id']}/assess-controls")
    return model


def _model_1_passes(client: TestClient) -> dict:
    """Credit Underwriting Scorecard — HIGH (70), all 9 controls present."""
    return _build_and_assess(
        client,
        name="Credit Underwriting Scorecard",
        business_function="Loan Underwriting",
        model_type="Third Party AI API",
        data_classification="Restricted",
        vendor_dependency="External Vendor",
        vendor_name="Acme Credit Co",
        has_documentation=True,
        has_independent_validation=True,
        has_explainability=True,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
    )


def _model_2_blocked_missing_controls(client: TestClient) -> dict:
    """Fraud Detection Vendor API — HIGH (70), missing independent_validation
    and explainability."""
    return _build_and_assess(
        client,
        has_documentation=True,
        has_independent_validation=False,
        has_explainability=False,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
    )


def _model_3_blocked_mixed(client: TestClient, db_session: Session) -> dict:
    """Customer Support GenAI — MEDIUM (55), missing drift_monitoring, plus a
    manually-created HIGH finding representing a discovered compliance gap
    outside the automated control checklist (control_key="vendor_risk" —
    a real P-1.3 mapping that P-1.4 deliberately excludes from the per-model
    tier checklist, since it's a vendor-assessment concern, not a per-model
    control)."""
    model = _build_and_assess(
        client,
        name="Customer Support GenAI",
        business_function="Customer Service",
        model_type="Machine Learning",
        data_classification="Confidential",
        vendor_dependency="Internal",
        vendor_name=None,
        has_documentation=True,
        has_independent_validation=True,
        has_drift_monitoring=False,
    )
    manual_finding = Finding(
        model_id=model["id"],
        title="Vendor risk assessment overdue",
        severity=Severity.HIGH,
        risk_description="A discovered compliance gap identified during manual review, outside the automated control checklist.",
        remediation="Complete vendor risk assessment and record findings.",
        regulatory_reference=resolve_reference(db_session, "vendor_risk"),
        control_key="vendor_risk",
        status=FindingStatus.OPEN,
    )
    db_session.add(manual_finding)
    db_session.commit()
    return model


# ---- The three demo models ----

def test_model_1_all_controls_present_allows(client: TestClient) -> None:
    model = _model_1_passes(client)
    response = client.post(f"/models/{model['id']}/deployment-check")
    assert response.status_code == 200
    body = response.json()

    assert body["decision"] == "ALLOW"
    assert body["risk_category"] == "HIGH"
    assert body["risk_score"] == 70
    assert body["overall_status"] == "PASS"
    assert body["open_findings_count"] == 0
    assert body["blocking_findings"] == []
    assert body["message"] == "All controls satisfied. Deployment allowed."


def test_model_2_missing_controls_blocks_with_two_rbi_references(client: TestClient) -> None:
    model = _model_2_blocked_missing_controls(client)
    response = client.post(f"/models/{model['id']}/deployment-check")
    assert response.status_code == 200
    body = response.json()

    assert body["decision"] == "BLOCKED"
    assert body["risk_category"] == "HIGH"
    assert body["risk_score"] == 70
    assert body["overall_status"] == "FAIL"
    assert body["open_findings_count"] == 2
    assert len(body["blocking_findings"]) == 2

    regulation_names = {bf["regulation_name"] for bf in body["blocking_findings"]}
    assert regulation_names == {
        "RBI Scale Based Regulation (SBR) Framework",
        "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI",
    }
    assert "RBI Scale Based Regulation (SBR) Framework" in body["message"]
    assert "RBI FREE-AI Committee" in body["message"]


def test_model_3_mixed_findings_blocks_including_manual_finding(
    client: TestClient, db_session: Session
) -> None:
    model = _model_3_blocked_mixed(client, db_session)
    response = client.post(f"/models/{model['id']}/deployment-check")
    assert response.status_code == 200
    body = response.json()

    assert body["decision"] == "BLOCKED"
    assert body["risk_category"] == "MEDIUM"
    assert body["risk_score"] == 55
    assert body["overall_status"] == "FAIL"
    assert body["open_findings_count"] == 2

    control_keys = {bf["control_key"] for bf in body["blocking_findings"]}
    assert control_keys == {"drift_monitoring", "vendor_risk"}
    severities = {bf["control_key"]: bf["severity"] for bf in body["blocking_findings"]}
    assert severities["drift_monitoring"] == "MEDIUM"
    assert severities["vendor_risk"] == "HIGH"


# ---- 404 paths ----

def test_missing_model_returns_404_envelope(client: TestClient) -> None:
    response = client.post("/models/999999/deployment-check")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "ModelNotFoundError"


def test_missing_risk_assessment_returns_404_envelope(client: TestClient) -> None:
    payload = make_model_payload()
    model = client.post("/models", json=payload).json()
    response = client.post(f"/models/{model['id']}/deployment-check")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "AssessmentNotFoundError"


def test_missing_control_assessment_returns_404_envelope(client: TestClient) -> None:
    payload = make_model_payload()
    model = client.post("/models", json=payload).json()
    client.post(f"/models/{model['id']}/assess")
    response = client.post(f"/models/{model['id']}/deployment-check")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "AssessmentNotFoundError"


# ---- Invariants ----

def test_rerunning_gate_on_unchanged_model_is_deterministic(client: TestClient) -> None:
    model = _model_2_blocked_missing_controls(client)
    first = client.post(f"/models/{model['id']}/deployment-check").json()
    second = client.post(f"/models/{model['id']}/deployment-check").json()

    # audit_log_id/checked_at legitimately differ — each check is its own
    # auditable event. The DECISION must be identical.
    assert first["decision"] == second["decision"]
    assert first["blocking_findings"] == second["blocking_findings"]
    assert first["message"] == second["message"]
    assert first["open_findings_count"] == second["open_findings_count"]
    assert first["audit_log_id"] != second["audit_log_id"]


def test_closed_findings_excluded_from_block(client: TestClient, db_session: Session) -> None:
    # Isolated from overall_status: start from a fully-passing model (so
    # overall_status stays PASS throughout), add one manual HIGH finding to
    # force a block, then close it and confirm the gate flips back to ALLOW.
    model = _model_1_passes(client)
    manual_finding = Finding(
        model_id=model["id"],
        title="Ad hoc compliance gap",
        severity=Severity.HIGH,
        risk_description="Discovered during manual review.",
        remediation="Resolve and record.",
        regulatory_reference=None,
        control_key="manual_review_gap",
        status=FindingStatus.OPEN,
    )
    db_session.add(manual_finding)
    db_session.commit()

    blocked = client.post(f"/models/{model['id']}/deployment-check").json()
    assert blocked["decision"] == "BLOCKED"
    assert blocked["open_findings_count"] == 1

    close_response = client.patch(f"/findings/{manual_finding.id}", json={"status": "CLOSED"})
    assert close_response.status_code == 200

    allowed = client.post(f"/models/{model['id']}/deployment-check").json()
    assert allowed["decision"] == "ALLOW"
    assert allowed["open_findings_count"] == 0
    assert allowed["blocking_findings"] == []


def test_audit_row_written_with_deployment_gate_checked_action(
    client: TestClient, db_session: Session
) -> None:
    model = _model_2_blocked_missing_controls(client)
    body = client.post(f"/models/{model['id']}/deployment-check").json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.model_id == model["id"], AuditLog.action == "DEPLOYMENT_GATE_CHECKED"
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].guardrail_result == body["decision"]
    assert rows[0].id == body["audit_log_id"]
