from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIModel
from app.schemas.discovery import DiscoveredAssetOut
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
