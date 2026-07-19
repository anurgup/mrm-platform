import asyncio
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.scanners import DiscoveredAsset, Scanner
from app.scanners.mock_scanners import (
    MockAzureMLScanner,
    MockGitHubScanner,
    MockMLflowScanner,
    MockSageMakerScanner,
)
from app.services import scanner as scanner_service
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


# ---- Individual mock scanners ----

def test_mock_mlflow_scanner_returns_2_assets() -> None:
    assets = asyncio.run(MockMLflowScanner().scan())
    assert len(assets) == 2
    assert {a.name for a in assets} == {"credit-risk-model-v5", "churn-prediction-exp"}
    assert all(a.source == "mlflow" for a in assets)


def test_mock_sagemaker_scanner_returns_1_asset() -> None:
    assets = asyncio.run(MockSageMakerScanner().scan())
    assert len(assets) == 1
    assert assets[0].name == "fraud-detection-endpoint"
    assert assets[0].source == "sagemaker"


def test_mock_github_scanner_returns_1_asset() -> None:
    assets = asyncio.run(MockGitHubScanner().scan())
    assert len(assets) == 1
    assert assets[0].name == "lending-ml-models"
    assert assets[0].source == "github"


def test_mock_azureml_scanner_returns_0_assets() -> None:
    assets = asyncio.run(MockAzureMLScanner().scan())
    assert assets == []


# ---- Orchestration ----

def test_discover_assets_aggregates_all_four(db_session: Session) -> None:
    assets = asyncio.run(scanner_service.discover_assets(db_session))
    assert len(assets) == 4
    assert {a.name for a in assets} == {
        "credit-risk-model-v5", "churn-prediction-exp",
        "fraud-detection-endpoint", "lending-ml-models",
    }


class _DuplicatingScanner(Scanner):
    async def scan(self) -> list[DiscoveredAsset]:
        return [
            DiscoveredAsset(name="dup-model", source="mlflow", environment="production"),
            DiscoveredAsset(name="dup-model", source="mlflow", environment="production"),
        ]


def test_deduplication_removes_duplicate_assets(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_service, "get_configured_scanners", lambda: [_DuplicatingScanner()])
    assets = asyncio.run(scanner_service.discover_assets(db_session))
    assert len(assets) == 1
    assert assets[0].name == "dup-model"


# ---- API ----

def test_scan_endpoint_returns_four_assets_all_unregistered(client: TestClient) -> None:
    response = client.post("/discovery/scan")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 4
    assert all(a["already_registered"] is False for a in body)


def test_registering_matching_model_flips_already_registered(client: TestClient) -> None:
    client.post("/models", json=make_model_payload(name="credit-risk-model-v5"))

    body = client.post("/discovery/scan").json()
    flagged = {a["name"]: a["already_registered"] for a in body}

    assert flagged["credit-risk-model-v5"] is True
    assert flagged["churn-prediction-exp"] is False
    assert flagged["fraud-detection-endpoint"] is False
    assert flagged["lending-ml-models"] is False


def test_already_registered_counts_match_partial_registration(client: TestClient) -> None:
    client.post("/models", json=make_model_payload(name="credit-risk-model-v5"))
    client.post("/models", json=make_model_payload(name="fraud-detection-endpoint"))

    body = client.post("/discovery/scan").json()
    registered = [a for a in body if a["already_registered"]]
    unregistered = [a for a in body if not a["already_registered"]]

    assert len(registered) == 2
    assert len(unregistered) == 2
    assert {a["name"] for a in registered} == {"credit-risk-model-v5", "fraud-detection-endpoint"}
