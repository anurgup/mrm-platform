from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    BusinessFunction,
    DataClassification,
    DeploymentStage,
    ModelType,
    VendorDependency,
)


class AIModelBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    business_function: BusinessFunction
    model_type: ModelType
    deployment_stage: DeploymentStage = DeploymentStage.DEVELOPMENT
    business_owner: str = Field(min_length=1)
    risk_owner: str = Field(min_length=1)
    technical_owner: str = Field(min_length=1)
    data_classification: DataClassification
    vendor_dependency: VendorDependency
    vendor_name: str | None = None
    llm_provider: str | None = None
    llm_model_name: str | None = None

    has_documentation: bool = False
    has_independent_validation: bool = False
    has_explainability: bool = False
    has_drift_monitoring: bool = False
    has_human_override: bool = False
    has_audit_logging: bool = False
    has_deployment_approval: bool = False


class AIModelCreate(AIModelBase):
    @model_validator(mode="after")
    def _require_vendor_name_for_external_vendor(self) -> "AIModelCreate":
        if self.vendor_dependency == VendorDependency.EXTERNAL_VENDOR and not self.vendor_name:
            raise ValueError(
                "vendor_name is required when vendor_dependency is 'External Vendor'"
            )
        return self

    @model_validator(mode="after")
    def _require_llm_provider_for_generative_ai(self) -> "AIModelCreate":
        if self.model_type == ModelType.GENERATIVE_AI and not self.llm_provider:
            raise ValueError("llm_provider is required when model_type is 'Generative AI'")
        return self


class AIModelUpdate(BaseModel):
    """Partial update. `name` is deliberately absent — model identity is stable
    and not updatable through this schema."""

    model_config = ConfigDict(protected_namespaces=())

    description: str | None = None
    business_function: BusinessFunction | None = None
    model_type: ModelType | None = None
    deployment_stage: DeploymentStage | None = None
    business_owner: str | None = Field(default=None, min_length=1)
    risk_owner: str | None = Field(default=None, min_length=1)
    technical_owner: str | None = Field(default=None, min_length=1)
    data_classification: DataClassification | None = None
    vendor_dependency: VendorDependency | None = None
    vendor_name: str | None = None
    llm_provider: str | None = None
    llm_model_name: str | None = None

    has_documentation: bool | None = None
    has_independent_validation: bool | None = None
    has_explainability: bool | None = None
    has_drift_monitoring: bool | None = None
    has_human_override: bool | None = None
    has_audit_logging: bool | None = None
    has_deployment_approval: bool | None = None


class AIModelOut(AIModelBase):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
