import re
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, GuidanceType, RegulatoryMapping
from app.services.regulatory import resolve_reference
from app.services.regulatory_seed import SEED_MAPPINGS, seed_regulatory_mappings

# Patterns typical of a fabricated/specific RBI circular citation. Seed data
# and any mapping written through this module must never match these — see
# the module docstring in app/services/regulatory_seed.py for why.
FABRICATED_CITATION_PATTERNS = [
    re.compile(r"circular\s*no", re.IGNORECASE),
    re.compile(r"RBI/\d{4}", re.IGNORECASE),
    re.compile(r"\d{4}-\d{2}/\d+"),  # e.g. "2016-17/45" style circular numbering
    re.compile(r"no\.\s?\d+", re.IGNORECASE),
]

BINDING_KEYS = {
    "independent_validation", "human_override", "audit_logging",
    "documentation", "vendor_risk",
}
EMERGING_KEYS = {"explainability", "drift_monitoring"}


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


def test_seed_is_idempotent(db_session: Session) -> None:
    seed_regulatory_mappings(db_session)
    seed_regulatory_mappings(db_session)
    rows = db_session.execute(select(RegulatoryMapping)).scalars().all()
    assert len(rows) == 7


def test_all_seven_control_keys_resolve(db_session: Session) -> None:
    seed_regulatory_mappings(db_session)
    for row in SEED_MAPPINGS:
        result = resolve_reference(db_session, row["control_key"])
        assert result is not None, f"expected {row['control_key']!r} to resolve"


def test_binding_emerging_split_correct(db_session: Session) -> None:
    seed_regulatory_mappings(db_session)
    binding = {
        m.control_key for m in db_session.execute(
            select(RegulatoryMapping).where(RegulatoryMapping.guidance_type == GuidanceType.BINDING)
        ).scalars().all()
    }
    emerging = {
        m.control_key for m in db_session.execute(
            select(RegulatoryMapping).where(RegulatoryMapping.guidance_type == GuidanceType.EMERGING)
        ).scalars().all()
    }
    assert binding == BINDING_KEYS
    assert emerging == EMERGING_KEYS


def test_list_filter_by_guidance_type(client: TestClient, db_session: Session) -> None:
    seed_regulatory_mappings(db_session)

    binding_response = client.get("/regulatory-mappings", params={"guidance_type": "BINDING"})
    assert binding_response.status_code == 200
    assert len(binding_response.json()) == 5

    emerging_response = client.get("/regulatory-mappings", params={"guidance_type": "EMERGING"})
    assert emerging_response.status_code == 200
    assert len(emerging_response.json()) == 2


def test_resolve_reference_shape_for_known_key(db_session: Session) -> None:
    seed_regulatory_mappings(db_session)
    result = resolve_reference(db_session, "audit_logging")
    assert result is not None
    assert set(result.keys()) == {"regulation_name", "reference_text", "guidance_type", "effective_note"}
    assert result["guidance_type"] == "BINDING"


def test_resolve_reference_returns_none_for_unknown_key(db_session: Session) -> None:
    seed_regulatory_mappings(db_session)
    assert resolve_reference(db_session, "not_a_real_control_key") is None


def test_create_and_update_write_regulatory_mapping_updated_audit_rows(
    client: TestClient, db_session: Session
) -> None:
    create_response = client.post("/regulatory-mappings", json={
        "control_key": "data_retention",
        "regulation_name": "RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices",
        "reference_text": "Illustrative placeholder for a future data retention control mapping.",
        "guidance_type": "BINDING",
        "effective_note": "IT Governance Master Direction",
    })
    assert create_response.status_code == 201

    update_response = client.patch(
        "/regulatory-mappings/data_retention", json={"effective_note": "Updated note"}
    )
    assert update_response.status_code == 200

    rows = db_session.execute(
        select(AuditLog).where(AuditLog.action == "REGULATORY_MAPPING_UPDATED")
    ).scalars().all()
    assert len(rows) == 2


def test_create_duplicate_control_key_returns_409(client: TestClient) -> None:
    payload = {
        "control_key": "data_retention",
        "regulation_name": "RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices",
        "reference_text": "Illustrative placeholder for a future data retention control mapping.",
        "guidance_type": "BINDING",
        "effective_note": None,
    }
    client.post("/regulatory-mappings", json=payload)
    response = client.post("/regulatory-mappings", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["type"] == "DuplicateRegulatoryMappingError"


def test_get_missing_mapping_returns_404_envelope(client: TestClient) -> None:
    response = client.get("/regulatory-mappings/not_a_real_control_key")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "RegulatoryMappingNotFoundError"


def test_no_fabricated_citation_patterns_in_seed_data() -> None:
    """Codifies the 'no invented citations' rule: seed data may name
    instruments, but must never contain a specific circular number, date, or
    clause reference that wasn't deliberately verified."""
    for row in SEED_MAPPINGS:
        for field in ("reference_text", "effective_note"):
            value = row.get(field)
            if not value:
                continue
            for pattern in FABRICATED_CITATION_PATTERNS:
                assert not pattern.search(str(value)), (
                    f"{row['control_key']}.{field} looks like a fabricated citation: {value!r}"
                )
