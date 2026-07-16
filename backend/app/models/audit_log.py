from datetime import datetime
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class AuditLog(Base):
    """Append-only audit trail (write/read behavior enforced in P-0.3 — here
    just the table)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[str] = mapped_column(default="system")
    timestamp: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    action: Mapped[str] = mapped_column(index=True)
    # Deliberately NOT a foreign key: audit entries must remain readable even
    # if the model they refer to is later deleted.
    model_id: Mapped[int | None]
    llm_provider_used: Mapped[str | None]
    guardrail_result: Mapped[str | None]
    risk_assessment_result: Mapped[str | None]
    report_generated: Mapped[bool | None]
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
