from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskCategory


class FactorContributionOut(BaseModel):
    key: str
    reason: str
    points: int


class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    risk_score: int
    risk_category: RiskCategory
    assessment_reason: str
    factor_breakdown: list[FactorContributionOut]
    assessed_at: datetime
