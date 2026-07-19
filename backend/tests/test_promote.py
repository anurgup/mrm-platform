from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditLog
from app.services.regulatory_seed import seed_regulatory_mappings


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


def _scan(client: TestClient) -> list[dict]:
    return client.post("/discovery/scan").json()


def _credit_risk_asset(client: TestClient) -> dict:
    return next(a for a in _scan(client) if a["name"] == "credit-risk-model-v5")


def test_promote_credit_risk_model_creates_model_with_sensible_defaults(
    client: TestClient,
) -> None:
    asset = _credit_risk_asset(client)
    response = client.post("/discovery/promote", json={"discovered_asset": asset})
    assert response.status_code == 201
    body = response.json()

    assert body["name"] == "credit-risk-model-v5"
    assert body["deployment_stage"] == "Production"
    assert body["business_owner"] == "Unknown"
    assert body["risk_owner"] == "Unassigned"
    assert body["technical_owner"] == "Unassigned"
    assert body["data_classification"] == "Restricted"
    assert body["vendor_dependency"] == "Internal"
    assert body["business_function"] == "Risk Analytics"
    assert body["model_type"] == "Machine Learning"
    for attestation in (
        "has_documentation", "has_independent_validation", "has_explainability",
        "has_drift_monitoring", "has_human_override", "has_audit_logging",
        "has_deployment_approval",
    ):
        assert body[attestation] is False


def test_promoting_same_asset_twice_returns_409(client: TestClient) -> None:
    asset = _credit_risk_asset(client)
    client.post("/discovery/promote", json={"discovered_asset": asset})
    response = client.post("/discovery/promote", json={"discovered_asset": asset})
    assert response.status_code == 409
    assert response.json()["error"]["type"] == "DuplicateModelError"


def test_promote_with_business_function_override(client: TestClient) -> None:
    asset = _credit_risk_asset(client)
    response = client.post("/discovery/promote", json={
        "discovered_asset": asset, "business_function": "Fraud Detection",
    })
    assert response.status_code == 201
    assert response.json()["business_function"] == "Fraud Detection"


def test_audit_row_written_for_promotion(client: TestClient, db_session: Session) -> None:
    asset = _credit_risk_asset(client)
    model = client.post("/discovery/promote", json={"discovered_asset": asset}).json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.model_id == model["id"], AuditLog.action == "MODEL_PROMOTED_FROM_DISCOVERY"
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].detail == {"source": "mlflow", "promoted_by": "system"}


def test_promoted_model_appears_in_inventory_list(client: TestClient) -> None:
    asset = _credit_risk_asset(client)
    client.post("/discovery/promote", json={"discovered_asset": asset})

    names = {m["name"] for m in client.get("/models").json()}
    assert "credit-risk-model-v5" in names


def test_can_immediately_assess_risk_on_promoted_model(client: TestClient) -> None:
    asset = _credit_risk_asset(client)
    model = client.post("/discovery/promote", json={"discovered_asset": asset}).json()

    response = client.post(f"/models/{model['id']}/assess")
    assert response.status_code == 201
    assert response.json()["risk_category"] in {"HIGH", "MEDIUM", "LOW"}


def test_promote_missing_discovered_asset_returns_422(client: TestClient) -> None:
    response = client.post("/discovery/promote", json={})
    assert response.status_code == 422


def test_promote_with_blank_discovered_asset_fields_returns_400(client: TestClient) -> None:
    response = client.post("/discovery/promote", json={
        "discovered_asset": {
            "name": "", "source": "", "environment": "", "owner": None, "description": None,
        },
    })
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "InvalidDiscoveredAssetError"


def test_scan_then_promote_full_workflow(client: TestClient) -> None:
    discovered = _scan(client)
    assert len(discovered) == 4

    target = next(a for a in discovered if a["name"] == "credit-risk-model-v5")
    promoted = client.post("/discovery/promote", json={"discovered_asset": target}).json()

    rescanned = _scan(client)
    flagged = next(a for a in rescanned if a["name"] == "credit-risk-model-v5")
    assert flagged["already_registered"] is True
    assert promoted["id"] is not None
