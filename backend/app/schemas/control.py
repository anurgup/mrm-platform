from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import FindingStatus, RiskCategory, Severity


class ControlAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    risk_category: RiskCategory
    controls_required: int
    controls_passed: int
    overall_status: str
    detail: dict[str, Any]
    assessed_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    title: str
    severity: Severity
    risk_description: str
    remediation: str
    regulatory_reference: dict[str, Any] | None
    control_key: str | None
    status: FindingStatus
    created_at: datetime


class ControlAssessmentWithFindings(BaseModel):
    control_assessment: ControlAssessmentOut
    findings: list[FindingOut]


class FindingStatusUpdate(BaseModel):
    status: FindingStatus
