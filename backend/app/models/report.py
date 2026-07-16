from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow
from app.models.enums import ReportType, sa_enum


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ai_models.id"))
    report_type: Mapped[ReportType] = mapped_column(sa_enum(ReportType))
    file_path: Mapped[str]
    generated_by: Mapped[str]
    generated_at: Mapped[datetime] = mapped_column(default=utcnow)
    audit_log_id: Mapped[int | None] = mapped_column(ForeignKey("audit_logs.id"))
