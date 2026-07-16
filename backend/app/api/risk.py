from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AssessmentNotFoundError
from app.schemas.risk import RiskAssessmentOut
from app.services import risk as service

router = APIRouter(tags=["risk"])


@router.post(
    "/models/{model_id}/assess", response_model=RiskAssessmentOut, status_code=status.HTTP_201_CREATED
)
async def assess_model(model_id: int, db: Session = Depends(get_db)) -> RiskAssessmentOut:
    assessment = service.assess_model(db, model_id)
    return RiskAssessmentOut.model_validate(assessment)


@router.get("/models/{model_id}/risk", response_model=RiskAssessmentOut)
async def get_latest_risk(model_id: int, db: Session = Depends(get_db)) -> RiskAssessmentOut:
    assessment = service.get_latest_assessment(db, model_id)
    if assessment is None:
        raise AssessmentNotFoundError(f"No risk assessment exists yet for model id={model_id}")
    return RiskAssessmentOut.model_validate(assessment)


@router.get("/models/{model_id}/risk/history", response_model=list[RiskAssessmentOut])
async def get_risk_history(model_id: int, db: Session = Depends(get_db)) -> list[RiskAssessmentOut]:
    history = service.get_assessment_history(db, model_id)
    return [RiskAssessmentOut.model_validate(a) for a in history]
