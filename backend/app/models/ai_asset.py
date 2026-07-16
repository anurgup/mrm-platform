from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow
from app.models.enums import AssetStatus, sa_enum


class AIAsset(Base):
    __tablename__ = "ai_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    source: Mapped[str]
    environment: Mapped[str]
    owner: Mapped[str] = mapped_column(default="Unknown")
    status: Mapped[AssetStatus] = mapped_column(
        sa_enum(AssetStatus), default=AssetStatus.NOT_REGISTERED
    )
    linked_model_id: Mapped[int | None] = mapped_column(ForeignKey("ai_models.id"))
    detected_at: Mapped[datetime] = mapped_column(default=utcnow)
