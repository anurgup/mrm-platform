"""Read-only queries over the audit trail. Deliberately kept separate from
app/services/audit.py (which is writes-only, per its own module docstring)
so that module's "this module exposes writes only" claim stays literally
true — reading the audit trail doesn't violate append-only, but it doesn't
belong in the writer module either."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def list_audit_logs(
    db: Session, *, model_id: int | None = None, limit: int = 100
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if model_id is not None:
        stmt = stmt.where(AuditLog.model_id == model_id)
    return list(db.execute(stmt).scalars().all())
