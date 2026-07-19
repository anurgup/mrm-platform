"""Promotes a discovered shadow-AI asset into the governed inventory —
one-click: discovered asset -> a new ai_models row with conservative
defaults, ready for a human to refine (assign real owners, confirm
business function, attest to real controls)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DuplicateModelError
from app.models import AIModel
from app.models.enums import (
    BusinessFunction,
    DataClassification,
    DeploymentStage,
    ModelType,
    VendorDependency,
)
from app.scanners import DiscoveredAsset
from app.services.audit import write_audit

# Source alone doesn't reliably predict what BUSINESS a model serves —
# deliberately no hints here. Every promoted model defaults to Risk
# Analytics until a human assigns the real business function.
SOURCE_BUSINESS_FUNCTION_HINTS: dict[str, BusinessFunction] = {}

# Source DOES weakly predict model shape: an MLflow/SageMaker/GitHub/AzureML
# find is almost certainly a trained ML model; an API gateway find is more
# likely a third-party API being called, not a model being run in-house.
SOURCE_MODEL_TYPE_HINTS: dict[str, ModelType] = {
    "mlflow": ModelType.MACHINE_LEARNING,
    "sagemaker": ModelType.MACHINE_LEARNING,
    "github": ModelType.MACHINE_LEARNING,
    "azureml": ModelType.MACHINE_LEARNING,
    "api_gateway": ModelType.THIRD_PARTY_AI_API,
}

ENVIRONMENT_TO_DEPLOYMENT_STAGE: dict[str, DeploymentStage] = {
    "production": DeploymentStage.PRODUCTION,
    "staging": DeploymentStage.TESTING,
    "testing": DeploymentStage.TESTING,
    "development": DeploymentStage.DEVELOPMENT,
}


def promote_asset_to_model(
    db: Session,
    discovered_asset: DiscoveredAsset,
    *,
    promoted_by: str = "system",
    business_function: BusinessFunction | None = None,
    model_type: ModelType | None = None,
) -> AIModel:
    existing = db.execute(
        select(AIModel).where(AIModel.name == discovered_asset.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateModelError(f"A model named {discovered_asset.name!r} is already registered")

    model = AIModel(
        name=discovered_asset.name,
        description=discovered_asset.description,
        business_function=business_function
        or SOURCE_BUSINESS_FUNCTION_HINTS.get(discovered_asset.source, BusinessFunction.RISK_ANALYTICS),
        model_type=model_type
        or SOURCE_MODEL_TYPE_HINTS.get(discovered_asset.source, ModelType.MACHINE_LEARNING),
        deployment_stage=ENVIRONMENT_TO_DEPLOYMENT_STAGE.get(
            discovered_asset.environment.lower(), DeploymentStage.DEVELOPMENT
        ),
        business_owner=discovered_asset.owner or "Unknown",
        risk_owner="Unassigned",
        technical_owner="Unassigned",
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.INTERNAL,
        # All seven governance attestations default to False at the column
        # level (conservative) — a shadow asset has proven nothing yet.
    )
    db.add(model)
    db.flush()
    write_audit(
        db, "MODEL_PROMOTED_FROM_DISCOVERY", user=promoted_by, model_id=model.id,
        detail={"source": discovered_asset.source, "promoted_by": promoted_by},
    )
    db.commit()
    db.refresh(model)
    return model
