from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import GuidanceType, sa_enum


class RegulatoryMapping(Base):
    __tablename__ = "regulatory_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    control_key: Mapped[str] = mapped_column(index=True)
    regulation_name: Mapped[str]
    reference_text: Mapped[str] = mapped_column(Text)
    guidance_type: Mapped[GuidanceType] = mapped_column(sa_enum(GuidanceType))
    effective_note: Mapped[str | None]
