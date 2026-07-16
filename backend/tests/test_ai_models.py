import time
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, BusinessFunction, DataClassification, ModelType, VendorDependency


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
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


def make_model_payload(**overrides: Any) -> dict[str, Any]:
    """Reusable factory for a valid AIModelCreate payload. Import this in
    later-wave engine tests instead of duplicating the boilerplate."""
    payload: dict[str, Any] = {
        "name": "Fraud Detection Vendor API",
        "description": "Third-party fraud scoring API.",
        "business_function": BusinessFunction.FRAUD_DETECTION.value,
        "model_type": ModelType.THIRD_PARTY_AI_API.value,
        "business_owner": "Priya Nair",
        "risk_owner": "Anurag Gupta",
        "technical_owner": "Sarah Connor",
        "data_classification": DataClassification.CONFIDENTIAL.value,
        "vendor_dependency": VendorDependency.EXTERNAL_VENDOR.value,
        "vendor_name": "Acme Fraud Co",
    }
    payload.update(overrides)
    return payload


def test_create_model_returns_201_and_echoes_fields(client: TestClient) -> None:
    response = client.post("/models", json=make_model_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "Fraud Detection Vendor API"
    assert body["vendor_name"] == "Acme Fraud Co"
    assert body["deployment_stage"] == "Development"
    assert body["has_documentation"] is False


def test_create_duplicate_name_returns_409_with_envelope(client: TestClient) -> None:
    client.post("/models", json=make_model_payload())
    response = client.post("/models", json=make_model_payload())
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["type"] == "DuplicateModelError"
    assert "already registered" in body["error"]["message"]


def test_external_vendor_without_vendor_name_returns_422(client: TestClient) -> None:
    payload = make_model_payload(vendor_name=None)
    response = client.post("/models", json=payload)
    assert response.status_code == 422


def test_generative_ai_without_llm_provider_returns_422(client: TestClient) -> None:
    payload = make_model_payload(
        name="Chat Assistant",
        model_type=ModelType.GENERATIVE_AI.value,
        llm_provider=None,
    )
    response = client.post("/models", json=payload)
    assert response.status_code == 422


def test_generative_ai_with_llm_provider_succeeds(client: TestClient) -> None:
    payload = make_model_payload(
        name="Chat Assistant",
        model_type=ModelType.GENERATIVE_AI.value,
        llm_provider="OpenAI",
        llm_model_name="gpt-4o",
    )
    response = client.post("/models", json=payload)
    assert response.status_code == 201


def test_get_existing_model_returns_200(client: TestClient) -> None:
    created = client.post("/models", json=make_model_payload()).json()
    response = client.get(f"/models/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_model_returns_404_with_envelope(client: TestClient) -> None:
    response = client.get("/models/999999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["type"] == "ModelNotFoundError"


def test_list_returns_created_models(client: TestClient) -> None:
    client.post("/models", json=make_model_payload(name="Model A"))
    client.post("/models", json=make_model_payload(name="Model B"))
    response = client.get("/models")
    assert response.status_code == 200
    names = {m["name"] for m in response.json()}
    assert {"Model A", "Model B"} <= names


def test_list_with_business_function_filter_narrows_results(client: TestClient) -> None:
    client.post("/models", json=make_model_payload(
        name="Fraud Model", business_function=BusinessFunction.FRAUD_DETECTION.value,
    ))
    client.post("/models", json=make_model_payload(
        name="Collections Model", business_function=BusinessFunction.COLLECTIONS.value,
    ))
    response = client.get("/models", params={"business_function": "Collections"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Collections Model"


def test_patch_updates_field_and_bumps_updated_at(client: TestClient) -> None:
    created = client.post("/models", json=make_model_payload()).json()
    time.sleep(0.01)
    response = client.patch(f"/models/{created['id']}", json={"business_owner": "New Owner"})
    assert response.status_code == 200
    body = response.json()
    assert body["business_owner"] == "New Owner"
    assert body["updated_at"] > created["updated_at"]


def test_patch_attempting_to_change_name_is_ignored(client: TestClient) -> None:
    created = client.post("/models", json=make_model_payload()).json()
    response = client.patch(f"/models/{created['id']}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == created["name"]


def test_retire_sets_deployment_stage_and_does_not_delete(client: TestClient) -> None:
    created = client.post("/models", json=make_model_payload()).json()
    response = client.post(f"/models/{created['id']}/retire")
    assert response.status_code == 200
    assert response.json()["deployment_stage"] == "Retired"

    still_there = client.get(f"/models/{created['id']}")
    assert still_there.status_code == 200
    assert still_there.json()["deployment_stage"] == "Retired"


def test_audit_rows_written_for_register_update_retire(
    client: TestClient, db_session: Session
) -> None:
    created = client.post("/models", json=make_model_payload()).json()
    model_id = created["id"]
    client.patch(f"/models/{model_id}", json={"business_owner": "New Owner"})
    client.post(f"/models/{model_id}/retire")

    rows = db_session.execute(
        select(AuditLog).where(AuditLog.model_id == model_id).order_by(AuditLog.id)
    ).scalars().all()
    actions = [row.action for row in rows]
    assert actions == ["MODEL_REGISTERED", "MODEL_UPDATED", "MODEL_RETIRED"]
