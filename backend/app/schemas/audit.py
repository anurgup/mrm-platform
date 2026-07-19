from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: str
    timestamp: datetime
    action: str
    model_id: int | None
    llm_provider_used: str | None
    guardrail_result: str | None
    risk_assessment_result: str | None
    report_generated: str | None
    detail: dict[str, Any]
