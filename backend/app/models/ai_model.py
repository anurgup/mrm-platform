from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow
from app.models.enums import (
    BusinessFunction,
    DataClassification,
    DeploymentStage,
    ModelType,
    VendorDependency,
    sa_enum,
)

if TYPE_CHECKING:
    from app.models.control_assessment import ControlAssessment
    from app.models.finding import Finding
    from app.models.risk_assessment import RiskAssessment


class AIModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    business_function: Mapped[BusinessFunction] = mapped_column(sa_enum(BusinessFunction))
    model_type: Mapped[ModelType] = mapped_column(sa_enum(ModelType))
    deployment_stage: Mapped[DeploymentStage] = mapped_column(
        sa_enum(DeploymentStage), default=DeploymentStage.DEVELOPMENT
    )
    business_owner: Mapped[str]
    risk_owner: Mapped[str]
    technical_owner: Mapped[str]
    data_classification: Mapped[DataClassification] = mapped_column(sa_enum(DataClassification))
    vendor_dependency: Mapped[VendorDependency] = mapped_column(sa_enum(VendorDependency))
    vendor_name: Mapped[str | None]
    llm_provider: Mapped[str | None]
    llm_model_name: Mapped[str | None]

    has_documentation: Mapped[bool] = mapped_column(default=False)
    has_independent_validation: Mapped[bool] = mapped_column(default=False)
    has_explainability: Mapped[bool] = mapped_column(default=False)
    has_drift_monitoring: Mapped[bool] = mapped_column(default=False)
    has_human_override: Mapped[bool] = mapped_column(default=False)
    has_audit_logging: Mapped[bool] = mapped_column(default=False)
    has_deployment_approval: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )
    control_assessments: Mapped[list["ControlAssessment"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )
