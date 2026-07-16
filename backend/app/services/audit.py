"""
Append-only audit writer.

`detail` is for structured metadata only — counts, ids, decisions, entity
*types* and *labels*. Callers MUST NOT pass raw customer text or detected PII
values (matched strings, spans of sensitive content, free-form user input)
into `detail`. This is a data-protection boundary, not a style preference:
anything written here is retained as a permanent audit record.

APPEND-ONLY: this module exposes writes only. There is no update/delete/edit
function for audit logs here, or anywhere else in the codebase — see
tests/test_audit.py for the structural guard tests that enforce this.

Transaction behavior: write_audit() flushes (not commits) the new row, so
its `.id` is available to the caller immediately (e.g. to store as
reports.audit_log_id) without ending the caller's transaction. Committing —
and therefore durably persisting the row — is the request boundary's
responsibility. Every function in this module is consistent with this: none
of them call db.commit().
"""

from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import AuditLog


def _value(x: Enum | str) -> str:
    return x.value if isinstance(x, Enum) else x


def write_audit(
    db: Session,
    action: str,
    *,
    user: str = "system",
    model_id: int | None = None,
    llm_provider_used: str | None = None,
    guardrail_result: str | None = None,
    risk_assessment_result: str | None = None,
    report_generated: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one immutable audit event. Returns the persisted row (flushed,
    with its id populated; not committed — see module docstring)."""
    row = AuditLog(
        user=user,
        timestamp=utcnow(),
        action=action,
        model_id=model_id,
        llm_provider_used=llm_provider_used,
        guardrail_result=guardrail_result,
        risk_assessment_result=risk_assessment_result,
        report_generated=report_generated,
        detail=detail if detail is not None else {},
    )
    db.add(row)
    db.flush()
    return row


def audit_risk(
    db: Session, model_id: int, category: Enum | str, user: str = "system"
) -> AuditLog:
    return write_audit(
        db, "RISK_ASSESSED", user=user, model_id=model_id,
        risk_assessment_result=_value(category),
    )


def audit_guardrail(
    db: Session, model_id: int, stage: Enum | str, decision: Enum | str, user: str = "system"
) -> AuditLog:
    return write_audit(
        db, "GUARDRAIL_EVALUATED", user=user, model_id=model_id,
        guardrail_result=f"{_value(stage)}:{_value(decision)}",
    )


def audit_report(
    db: Session, model_id: int, report_path: str, user: str = "system"
) -> AuditLog:
    return write_audit(
        db, "REPORT_GENERATED", user=user, model_id=model_id,
        report_generated=report_path,
    )
