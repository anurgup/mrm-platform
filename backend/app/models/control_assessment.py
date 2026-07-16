from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow
from app.models.enums import RiskCategory, sa_enum

if TYPE_CHECKING:
    from app.models.ai_model import AIModel


class ControlAssessment(Base):
    __tablename__ = "control_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ai_models.id"))
    risk_category: Mapped[RiskCategory] = mapped_column(sa_enum(RiskCategory))
    controls_required: Mapped[int]
    controls_passed: Mapped[int]
    overall_status: Mapped[str]
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assessed_at: Mapped[datetime] = mapped_column(default=utcnow)

    model: Mapped["AIModel"] = relationship(back_populates="control_assessments")
