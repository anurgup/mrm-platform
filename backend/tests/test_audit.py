import inspect
import re
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import AuditLog, GuardrailAction, GuardrailStage, RiskCategory
from app.services import audit as audit_module
from app.services.audit import audit_guardrail, audit_report, audit_risk, write_audit

APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Patterns that would indicate someone mutating or deleting an audit row.
# Keep this list easy to extend — it's the whole point of the guard test.
FORBIDDEN_PATTERNS = [
    r"delete\(\s*AuditLog",
    r"AuditLog\)\.delete\(",
    r"update\(\s*AuditLog",
    r"AuditLog\)\.update\(",
    r"\.query\(AuditLog\).*\.delete\(",
    r"\.query\(AuditLog\).*\.update\(",
    r"session\.delete\(\s*\w*audit",
]
FORBIDDEN_NAME_SUBSTRINGS = ("update", "delete", "edit", "remove", "patch")


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_write_audit_persists_row_with_id_and_utc_timestamp(db: Session) -> None:
    row = write_audit(db, "MODEL_CREATED")
    assert row.id is not None
    assert row.timestamp.tzinfo is not None
    assert row.timestamp.utcoffset() == timezone.utc.utcoffset(None)


def test_detail_defaults_to_empty_dict(db: Session) -> None:
    row = write_audit(db, "MODEL_CREATED")
    assert row.detail == {}


def test_detail_passthrough_when_provided(db: Session) -> None:
    row = write_audit(db, "MODEL_CREATED", detail={"model_count": 3})
    assert row.detail == {"model_count": 3}


def test_audit_risk_sets_expected_fields(db: Session) -> None:
    row = audit_risk(db, model_id=1, category=RiskCategory.HIGH)
    assert row.action == "RISK_ASSESSED"
    assert row.model_id == 1
    assert row.risk_assessment_result == "HIGH"


def test_audit_guardrail_sets_expected_fields(db: Session) -> None:
    row = audit_guardrail(db, model_id=1, stage=GuardrailStage.INPUT, decision=GuardrailAction.MASK)
    assert row.action == "GUARDRAIL_EVALUATED"
    assert row.guardrail_result == "INPUT:MASK"


def test_audit_report_sets_expected_fields(db: Session) -> None:
    row = audit_report(db, model_id=1, report_path="/reports/model-1.pdf")
    assert row.action == "REPORT_GENERATED"
    assert row.report_generated == "/reports/model-1.pdf"


def test_two_writes_produce_two_distinct_rows(db: Session) -> None:
    first = write_audit(db, "MODEL_CREATED")
    second = write_audit(db, "MODEL_CREATED")
    assert first.id != second.id
    db.flush()
    assert db.query(AuditLog).count() == 2


def test_audit_module_exposes_no_mutation_functions() -> None:
    """No update/delete/edit/remove/patch callable may exist in this module —
    audit_logs is append-only. This is the guard against a future contributor
    quietly adding one."""
    own_functions = [
        name
        for name, obj in inspect.getmembers(audit_module, inspect.isfunction)
        if obj.__module__ == audit_module.__name__
    ]
    assert own_functions, "expected write_audit and helpers to be discoverable"
    for name in own_functions:
        lowered = name.lower()
        for forbidden in FORBIDDEN_NAME_SUBSTRINGS:
            assert forbidden not in lowered, (
                f"app.services.audit.{name} looks like a mutation function "
                f"(matches {forbidden!r}) — audit_logs must be append-only"
            )


def test_no_delete_or_update_of_audit_logs_anywhere_in_app() -> None:
    """Repo-level guard: scans the whole app/ source tree, not just this
    module, so a delete/update snuck in elsewhere would still be caught."""
    combined = re.compile("|".join(FORBIDDEN_PATTERNS))
    violations = []
    for path in APP_DIR.rglob("*.py"):
        text = path.read_text()
        if combined.search(text):
            violations.append(str(path.relative_to(APP_DIR.parent)))
    assert violations == [], f"found audit_logs mutation code in: {violations}"
