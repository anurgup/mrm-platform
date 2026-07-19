from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AssessmentNotFoundError
from app.schemas.control import (
    ControlAssessmentOut,
    ControlAssessmentWithFindings,
    FindingOut,
    FindingStatusUpdate,
)
from app.services import control as service

router = APIRouter(tags=["control"])


@router.post(
    "/models/{model_id}/assess-controls",
    response_model=ControlAssessmentWithFindings,
    status_code=status.HTTP_201_CREATED,
)
async def assess_model_controls(
    model_id: int, db: Session = Depends(get_db)
) -> ControlAssessmentWithFindings:
    assessment, findings = service.assess_model_controls(db, model_id)
    return ControlAssessmentWithFindings(
        control_assessment=ControlAssessmentOut.model_validate(assessment),
        findings=[FindingOut.model_validate(f) for f in findings],
    )


@router.get("/models/{model_id}/controls", response_model=ControlAssessmentOut)
async def get_latest_controls(model_id: int, db: Session = Depends(get_db)) -> ControlAssessmentOut:
    assessment = service.get_latest_control_assessment(db, model_id)
    if assessment is None:
        raise AssessmentNotFoundError(f"No control assessment exists yet for model id={model_id}")
    return ControlAssessmentOut.model_validate(assessment)


@router.get("/models/{model_id}/findings", response_model=list[FindingOut])
async def get_model_findings(model_id: int, db: Session = Depends(get_db)) -> list[FindingOut]:
    findings = service.get_control_findings(db, model_id)
    return [FindingOut.model_validate(f) for f in findings]


@router.patch("/findings/{finding_id}", response_model=FindingOut)
async def update_finding_status(
    finding_id: int, payload: FindingStatusUpdate, db: Session = Depends(get_db)
) -> FindingOut:
    finding = service.update_finding_status(db, finding_id, payload.status)
    return FindingOut.model_validate(finding)
