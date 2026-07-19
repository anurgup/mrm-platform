from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
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


def test_list_all_audit_logs(client: TestClient) -> None:
    client.post("/models", json=make_model_payload(name="Model A"))
    client.post("/models", json=make_model_payload(name="Model B"))

    response = client.get("/audit-logs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {row["action"] for row in body} == {"MODEL_REGISTERED"}


def test_filter_audit_logs_by_model_id(client: TestClient) -> None:
    model_a = client.post("/models", json=make_model_payload(name="Model A")).json()
    client.post("/models", json=make_model_payload(name="Model B"))
    client.post(f"/models/{model_a['id']}/assess")

    response = client.get("/audit-logs", params={"model_id": model_a["id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(row["model_id"] == model_a["id"] for row in body)
    assert {row["action"] for row in body} == {"MODEL_REGISTERED", "RISK_ASSESSED"}


def test_audit_logs_newest_first(client: TestClient) -> None:
    model = client.post("/models", json=make_model_payload()).json()
    client.post(f"/models/{model['id']}/assess")

    response = client.get("/audit-logs", params={"model_id": model["id"]}).json()
    assert response[0]["action"] == "RISK_ASSESSED"
    assert response[1]["action"] == "MODEL_REGISTERED"
