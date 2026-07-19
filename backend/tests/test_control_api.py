from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AIModel, AuditLog, Finding
from app.services.regulatory_seed import seed_regulatory_mappings
from tests.test_ai_models import make_model_payload


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    # The app's real startup auto-seeds regulatory mappings via its lifespan,
    # but that lifespan runs against the production SessionLocal, not this
    # isolated test DB (which get_db is overridden to point at instead) —
    # so tests must seed it explicitly to get the same baseline state.
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


def _register_and_assess_risk(client: TestClient, **overrides: object) -> dict:
    """Registers a model (default payload scores HIGH — Fraud Detection +
    Third Party AI API + Confidential + External Vendor = 70) and runs a
    risk assessment, since control assessment requires a risk tier first."""
    payload = make_model_payload(**overrides)
    model = client.post("/models", json=payload).json()
    client.post(f"/models/{model['id']}/assess")
    return model


def test_assess_controls_persists_and_matches_counts(client: TestClient) -> None:
    model = _register_and_assess_risk(client)
    response = client.post(f"/models/{model['id']}/assess-controls")
    assert response.status_code == 201
    body = response.json()

    assessment = body["control_assessment"]
    assert assessment["model_id"] == model["id"]
    assert assessment["risk_category"] == "HIGH"
    assert assessment["controls_required"] == 9
    # Default payload leaves all seven boolean attestations False; only
    # model_owner/risk_owner pass (business_owner/risk_owner are required
    # non-empty by P-3.1's schema), so 2 pass, 7 findings.
    assert assessment["controls_passed"] == 2
    assert assessment["overall_status"] == "FAIL"
    assert len(body["findings"]) == 7


def test_reassess_creates_new_assessment_but_no_duplicate_findings(
    client: TestClient, db_session: Session
) -> None:
    model = _register_and_assess_risk(client)
    first = client.post(f"/models/{model['id']}/assess-controls").json()
    second = client.post(f"/models/{model['id']}/assess-controls").json()

    assert first["control_assessment"]["id"] != second["control_assessment"]["id"]
    assert len(second["findings"]) == 7
    # Same finding ids returned both times — idempotency via control_key,
    # not a fresh set of rows.
    assert {f["id"] for f in first["findings"]} == {f["id"] for f in second["findings"]}

    all_findings = db_session.execute(
        select(Finding).where(Finding.model_id == model["id"])
    ).scalars().all()
    assert len(all_findings) == 7


def test_high_model_all_controls_present_passes_with_no_findings(client: TestClient) -> None:
    model = _register_and_assess_risk(
        client,
        has_documentation=True,
        has_independent_validation=True,
        has_explainability=True,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
    )
    response = client.post(f"/models/{model['id']}/assess-controls")
    body = response.json()

    assert body["control_assessment"]["overall_status"] == "PASS"
    assert body["control_assessment"]["controls_passed"] == 9
    assert body["findings"] == []


def test_missing_independent_validation_creates_finding_with_regulatory_reference(
    client: TestClient,
) -> None:
    model = _register_and_assess_risk(
        client,
        has_documentation=True,
        has_independent_validation=False,
        has_explainability=True,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
    )
    body = client.post(f"/models/{model['id']}/assess-controls").json()

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["control_key"] == "independent_validation"
    assert finding["severity"] == "HIGH"
    assert finding["regulatory_reference"] is not None
    assert finding["regulatory_reference"]["regulation_name"] == "RBI Scale Based Regulation (SBR) Framework"


def test_deployment_approval_missing_has_no_regulatory_reference_and_does_not_crash(
    client: TestClient,
) -> None:
    # deployment_approval has no P-1.3 regulatory_mapping row (internal
    # process control, not RBI-specific) — same "unmapped control" case as
    # model_owner/risk_owner, but reachable through the real API (unlike
    # business_owner/risk_owner, which P-3.1's schema requires non-empty,
    # so has_model_owner/has_risk_owner can never be False via this route).
    model = _register_and_assess_risk(
        client,
        has_documentation=True,
        has_independent_validation=True,
        has_explainability=True,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=False,
    )
    body = client.post(f"/models/{model['id']}/assess-controls").json()

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["control_key"] == "deployment_approval"
    assert finding["regulatory_reference"] is None


def test_model_owner_missing_has_no_regulatory_reference_service_level(
    client: TestClient, db_session: Session
) -> None:
    # The literal model_owner case from the spec: business_owner empty.
    # Unreachable through AIModelCreate (P-3.1 requires it non-empty), so
    # this manipulates the persisted ORM row directly to set up the state —
    # a legitimate way to test this service's graceful handling without
    # relitigating P-3.1's validation rule.
    model = _register_and_assess_risk(client, has_documentation=True)
    ai_model = db_session.get(AIModel, model["id"])
    ai_model.business_owner = ""
    db_session.commit()

    from app.services.control import assess_model_controls

    _assessment, findings = assess_model_controls(db_session, model["id"])
    owner_finding = next(f for f in findings if f.control_key == "model_owner")
    assert owner_finding.regulatory_reference is None


def test_get_findings_and_patch_status(client: TestClient) -> None:
    model = _register_and_assess_risk(client)
    client.post(f"/models/{model['id']}/assess-controls")

    findings = client.get(f"/models/{model['id']}/findings").json()
    assert len(findings) == 7
    finding_id = findings[0]["id"]

    patched = client.patch(f"/findings/{finding_id}", json={"status": "IN_REMEDIATION"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "IN_REMEDIATION"

    refreshed = client.get(f"/models/{model['id']}/findings").json()
    updated = next(f for f in refreshed if f["id"] == finding_id)
    assert updated["status"] == "IN_REMEDIATION"


def test_assess_controls_missing_model_returns_404_envelope(client: TestClient) -> None:
    response = client.post("/models/999999/assess-controls")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "ModelNotFoundError"


def test_assess_controls_without_risk_assessment_returns_404_envelope(client: TestClient) -> None:
    payload = make_model_payload()
    model = client.post("/models", json=payload).json()
    response = client.post(f"/models/{model['id']}/assess-controls")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "AssessmentNotFoundError"


def test_audit_row_written_with_control_assessed_action(
    client: TestClient, db_session: Session
) -> None:
    model = _register_and_assess_risk(client)
    body = client.post(f"/models/{model['id']}/assess-controls").json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.model_id == model["id"], AuditLog.action == "CONTROL_ASSESSED"
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].risk_assessment_result == body["control_assessment"]["overall_status"]
