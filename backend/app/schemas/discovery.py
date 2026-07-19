from pydantic import BaseModel


class DiscoveredAssetOut(BaseModel):
    name: str
    source: str
    environment: str
    owner: str | None
    description: str | None

    # Whether this asset's name already matches a registered model.
    already_registered: bool = False
