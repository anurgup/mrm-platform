from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ModelNotFoundError
from app.models.enums import BusinessFunction, DeploymentStage, ModelType
from app.schemas.ai_model import AIModelCreate, AIModelOut, AIModelUpdate
from app.services import ai_model as service

router = APIRouter(prefix="/models", tags=["inventory"])


@router.post("", response_model=AIModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(payload: AIModelCreate, db: Session = Depends(get_db)) -> AIModelOut:
    model = service.create_model(db, payload)
    return AIModelOut.model_validate(model)


@router.get("", response_model=list[AIModelOut])
async def list_models(
    business_function: BusinessFunction | None = Query(default=None),
    model_type: ModelType | None = Query(default=None),
    deployment_stage: DeploymentStage | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AIModelOut]:
    models = service.list_models(
        db,
        business_function=business_function,
        model_type=model_type,
        deployment_stage=deployment_stage,
    )
    return [AIModelOut.model_validate(m) for m in models]


@router.get("/{model_id}", response_model=AIModelOut)
async def get_model(model_id: int, db: Session = Depends(get_db)) -> AIModelOut:
    model = service.get_model(db, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")
    return AIModelOut.model_validate(model)


@router.patch("/{model_id}", response_model=AIModelOut)
async def update_model(
    model_id: int, payload: AIModelUpdate, db: Session = Depends(get_db)
) -> AIModelOut:
    model = service.update_model(db, model_id, payload)
    return AIModelOut.model_validate(model)


@router.post("/{model_id}/retire", response_model=AIModelOut)
async def retire_model(model_id: int, db: Session = Depends(get_db)) -> AIModelOut:
    model = service.retire_model(db, model_id)
    return AIModelOut.model_validate(model)
