from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import RiskCategory, Severity


class BlockingFinding(BaseModel):
    control_key: str | None
    title: str
    severity: Severity
    regulation_name: str | None
    reference_text: str | None


class DeploymentCheckResult(BaseModel):
    model_id: int
    decision: Literal["ALLOW", "BLOCKED"]
    risk_category: RiskCategory
    risk_score: int
    controls_required: int
    controls_passed: int
    overall_status: str
    open_findings_count: int
    blocking_findings: list[BlockingFinding]
    message: str
    checked_at: datetime
    audit_log_id: int
