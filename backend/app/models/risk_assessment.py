from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow
from app.models.enums import RiskCategory, sa_enum

if TYPE_CHECKING:
    from app.models.ai_model import AIModel


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ai_models.id"))
    risk_score: Mapped[int]
    risk_category: Mapped[RiskCategory] = mapped_column(sa_enum(RiskCategory))
    assessment_reason: Mapped[str] = mapped_column(Text)
    factor_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assessed_at: Mapped[datetime] = mapped_column(default=utcnow)

    model: Mapped["AIModel"] = relationship(back_populates="risk_assessments")
