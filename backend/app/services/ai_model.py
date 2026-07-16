"""Pure DB operations for the AI model inventory. No HTTP concerns here —
routers call these and map DomainErrors to responses."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DuplicateModelError, ModelNotFoundError
from app.models import AIModel
from app.models.enums import BusinessFunction, DeploymentStage, ModelType
from app.schemas.ai_model import AIModelCreate, AIModelUpdate
from app.services.audit import write_audit


def create_model(db: Session, data: AIModelCreate) -> AIModel:
    existing = db.execute(select(AIModel).where(AIModel.name == data.name)).scalar_one_or_none()
    if existing is not None:
        raise DuplicateModelError(f"A model named {data.name!r} is already registered")

    model = AIModel(**data.model_dump())
    db.add(model)
    db.flush()
    write_audit(db, "MODEL_REGISTERED", model_id=model.id, detail={"name": model.name})
    db.commit()
    db.refresh(model)
    return model


def get_model(db: Session, model_id: int) -> AIModel | None:
    return db.get(AIModel, model_id)


def list_models(
    db: Session,
    *,
    business_function: BusinessFunction | None = None,
    model_type: ModelType | None = None,
    deployment_stage: DeploymentStage | None = None,
) -> list[AIModel]:
    stmt = select(AIModel)
    if business_function is not None:
        stmt = stmt.where(AIModel.business_function == business_function)
    if model_type is not None:
        stmt = stmt.where(AIModel.model_type == model_type)
    if deployment_stage is not None:
        stmt = stmt.where(AIModel.deployment_stage == deployment_stage)
    return list(db.execute(stmt).scalars().all())


def update_model(db: Session, model_id: int, data: AIModelUpdate) -> AIModel:
    model = db.get(AIModel, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(model, field, value)

    db.flush()
    write_audit(db, "MODEL_UPDATED", model_id=model.id, detail={"fields": sorted(changes)})
    db.commit()
    db.refresh(model)
    return model


def retire_model(db: Session, model_id: int) -> AIModel:
    model = db.get(AIModel, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")

    model.deployment_stage = DeploymentStage.RETIRED
    db.flush()
    write_audit(db, "MODEL_RETIRED", model_id=model.id)
    db.commit()
    db.refresh(model)
    return model
