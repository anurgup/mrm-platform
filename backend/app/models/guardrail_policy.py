from typing import Any

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import GuardrailAction, GuardrailStage, sa_enum


class GuardrailPolicy(Base):
    __tablename__ = "guardrail_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    stage: Mapped[GuardrailStage] = mapped_column(sa_enum(GuardrailStage))
    detector: Mapped[str]
    action: Mapped[GuardrailAction] = mapped_column(sa_enum(GuardrailAction))
    is_enabled: Mapped[bool] = mapped_column(default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
