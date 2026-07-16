import time
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.engines.risk import RiskInput, assess
from app.main import app
from app.models import AuditLog, BusinessFunction, DataClassification, ModelType, VendorDependency
from tests.test_ai_models import make_model_payload


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


def _register_model(client: TestClient, **overrides: object) -> dict:
    payload = make_model_payload(**overrides)
    response = client.post("/models", json=payload)
    assert response.status_code == 201
    return response.json()


def test_assess_persists_and_matches_pure_engine_result(client: TestClient) -> None:
    model = _register_model(client)

    # Compute the expected result independently, straight from the pure
    # engine — this proves persistence didn't distort the engine's output.
    expected = assess(RiskInput(
        business_function=BusinessFunction(model["business_function"]),
        model_type=ModelType(model["model_type"]),
        data_classification=DataClassification(model["data_classification"]),
        vendor_dependency=VendorDependency(model["vendor_dependency"]),
    ))

    response = client.post(f"/models/{model['id']}/assess")
    assert response.status_code == 201
    body = response.json()

    assert body["risk_score"] == expected.score
    assert body["risk_category"] == expected.category.value
    assert body["assessment_reason"] == expected.explanation
    assert [f["points"] for f in body["factor_breakdown"]] == [
        f.points for f in expected.factor_breakdown
    ]


def test_persisted_factor_breakdown_round_trips_and_sums_to_score(client: TestClient) -> None:
    model = _register_model(client)
    body = client.post(f"/models/{model['id']}/assess").json()
    assert sum(f["points"] for f in body["factor_breakdown"]) == body["risk_score"]
    for factor in body["factor_breakdown"]:
        assert {"key", "reason", "points"} <= factor.keys()


def test_audit_row_written_with_correct_category(
    client: TestClient, db_session: Session
) -> None:
    model = _register_model(client)
    body = client.post(f"/models/{model['id']}/assess").json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.model_id == model["id"], AuditLog.action == "RISK_ASSESSED"
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].risk_assessment_result == body["risk_category"]


def test_assess_missing_model_returns_404_envelope(client: TestClient) -> None:
    response = client.post("/models/999999/assess")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "ModelNotFoundError"


def test_get_risk_before_assessment_returns_404(client: TestClient) -> None:
    model = _register_model(client)
    response = client.get(f"/models/{model['id']}/risk")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "AssessmentNotFoundError"


def test_get_risk_after_assessment_returns_latest(client: TestClient) -> None:
    model = _register_model(client)
    assessed = client.post(f"/models/{model['id']}/assess").json()

    response = client.get(f"/models/{model['id']}/risk")
    assert response.status_code == 200
    assert response.json()["id"] == assessed["id"]
    assert response.json()["risk_score"] == assessed["risk_score"]


def test_reassess_creates_history_with_two_rows_newest_first(client: TestClient) -> None:
    model = _register_model(client)
    first = client.post(f"/models/{model['id']}/assess").json()
    time.sleep(0.01)
    second = client.post(f"/models/{model['id']}/assess").json()

    history = client.get(f"/models/{model['id']}/risk/history").json()
    assert len(history) == 2
    assert history[0]["id"] == second["id"]
    assert history[1]["id"] == first["id"]

    latest = client.get(f"/models/{model['id']}/risk").json()
    assert latest["id"] == second["id"]


def test_determinism_through_api_same_unchanged_model_assessed_twice(client: TestClient) -> None:
    model = _register_model(client)
    first = client.post(f"/models/{model['id']}/assess").json()
    second = client.post(f"/models/{model['id']}/assess").json()
    assert first["risk_score"] == second["risk_score"]
    assert first["risk_category"] == second["risk_category"]
    assert first["factor_breakdown"] == second["factor_breakdown"]
