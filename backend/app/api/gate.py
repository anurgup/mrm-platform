from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.gate import DeploymentCheckResult
from app.services import gate as service

router = APIRouter(tags=["gate"])


@router.post("/models/{model_id}/deployment-check", response_model=DeploymentCheckResult)
async def check_deployment(model_id: int, db: Session = Depends(get_db)) -> DeploymentCheckResult:
    return service.check_deployment(db, model_id)
