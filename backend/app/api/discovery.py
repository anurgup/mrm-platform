from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import InvalidDiscoveredAssetError
from app.models import AIModel
from app.scanners import DiscoveredAsset
from app.schemas.ai_model import AIModelOut
from app.schemas.discovery import DiscoveredAssetOut, PromoteAssetRequest
from app.services.discovery import promote_asset_to_model
from app.services.scanner import discover_assets

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/scan", response_model=list[DiscoveredAssetOut])
async def scan(db: Session = Depends(get_db)) -> list[DiscoveredAssetOut]:
    assets = await discover_assets(db)

    registered_names = set(
        db.execute(
            select(AIModel.name).where(AIModel.name.in_({a.name for a in assets}))
        ).scalars().all()
    )

    return [
        DiscoveredAssetOut(
            name=asset.name,
            source=asset.source,
            environment=asset.environment,
            owner=asset.owner,
            description=asset.description,
            already_registered=asset.name in registered_names,
        )
        for asset in assets
    ]


@router.post("/promote", response_model=AIModelOut, status_code=status.HTTP_201_CREATED)
async def promote(payload: PromoteAssetRequest, db: Session = Depends(get_db)) -> AIModelOut:
    asset = payload.discovered_asset
    if not asset.name.strip() or not asset.source.strip() or not asset.environment.strip():
        raise InvalidDiscoveredAssetError(
            "discovered_asset is missing required details (name/source/environment)"
        )

    model = promote_asset_to_model(
        db,
        DiscoveredAsset(
            name=asset.name, source=asset.source, environment=asset.environment,
            owner=asset.owner, description=asset.description,
        ),
        business_function=payload.business_function,
        model_type=payload.model_type,
    )
    return AIModelOut.model_validate(model)
