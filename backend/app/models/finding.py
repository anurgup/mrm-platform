from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow
from app.models.enums import FindingStatus, Severity, sa_enum

if TYPE_CHECKING:
    from app.models.ai_model import AIModel


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ai_models.id"))
    title: Mapped[str]
    severity: Mapped[Severity] = mapped_column(sa_enum(Severity))
    risk_description: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str] = mapped_column(Text)
    regulatory_reference: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    control_key: Mapped[str | None]
    status: Mapped[FindingStatus] = mapped_column(sa_enum(FindingStatus), default=FindingStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    model: Mapped["AIModel"] = relationship(back_populates="findings")
    remediation_actions: Mapped[list["RemediationAction"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    action: Mapped[str] = mapped_column(Text)
    owner: Mapped[str]
    due_date: Mapped[date | None] = mapped_column(Date)
    completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    finding: Mapped["Finding"] = relationship(back_populates="remediation_actions")
