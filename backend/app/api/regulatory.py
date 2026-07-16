from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import RegulatoryMappingNotFoundError
from app.models.enums import GuidanceType
from app.schemas.regulatory import RegulatoryMappingCreate, RegulatoryMappingOut, RegulatoryMappingUpdate
from app.services import regulatory as service

router = APIRouter(prefix="/regulatory-mappings", tags=["regulatory"])


@router.get("", response_model=list[RegulatoryMappingOut])
async def list_mappings(
    guidance_type: GuidanceType | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RegulatoryMappingOut]:
    mappings = service.list_mappings(db, guidance_type=guidance_type)
    return [RegulatoryMappingOut.model_validate(m) for m in mappings]


@router.get("/{control_key}", response_model=RegulatoryMappingOut)
async def get_mapping(control_key: str, db: Session = Depends(get_db)) -> RegulatoryMappingOut:
    mapping = service.get_mapping(db, control_key)
    if mapping is None:
        raise RegulatoryMappingNotFoundError(f"No regulatory mapping for control_key={control_key!r}")
    return RegulatoryMappingOut.model_validate(mapping)


@router.post("", response_model=RegulatoryMappingOut, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    payload: RegulatoryMappingCreate, db: Session = Depends(get_db)
) -> RegulatoryMappingOut:
    mapping = service.create_mapping(db, payload)
    return RegulatoryMappingOut.model_validate(mapping)


@router.patch("/{control_key}", response_model=RegulatoryMappingOut)
async def update_mapping(
    control_key: str, payload: RegulatoryMappingUpdate, db: Session = Depends(get_db)
) -> RegulatoryMappingOut:
    mapping = service.update_mapping(db, control_key, payload)
    return RegulatoryMappingOut.model_validate(mapping)
