from pydantic import BaseModel

from app.models.enums import BusinessFunction, ModelType


class DiscoveredAssetOut(BaseModel):
    name: str
    source: str
    environment: str
    owner: str | None
    description: str | None

    # Whether this asset's name already matches a registered model.
    already_registered: bool = False


class PromoteAssetRequest(BaseModel):
    discovered_asset: DiscoveredAssetOut
    business_function: BusinessFunction | None = None  # override the inferred default
    model_type: ModelType | None = None  # override the inferred default
