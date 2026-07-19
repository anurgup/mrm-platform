from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.audit import AuditLogOut
from app.services.audit_query import list_audit_logs

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def get_audit_logs(
    model_id: int | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    rows = list_audit_logs(db, model_id=model_id, limit=limit)
    return [AuditLogOut.model_validate(r) for r in rows]
