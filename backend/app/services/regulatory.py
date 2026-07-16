"""Regulatory mapping lookups and admin CRUD.

resolve_reference() is the contract the control engine (P-1.4) and findings
(P-1.5) will call to anchor a governance gap to a regulatory reference."""

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DuplicateRegulatoryMappingError, RegulatoryMappingNotFoundError
from app.models import GuidanceType, RegulatoryMapping
from app.schemas.regulatory import RegulatoryMappingCreate, RegulatoryMappingUpdate
from app.services.audit import write_audit


class ResolvedReference(TypedDict):
    regulation_name: str
    reference_text: str
    guidance_type: str
    effective_note: str | None


def get_mapping(db: Session, control_key: str) -> RegulatoryMapping | None:
    return db.execute(
        select(RegulatoryMapping).where(RegulatoryMapping.control_key == control_key)
    ).scalar_one_or_none()


def list_mappings(
    db: Session, *, guidance_type: GuidanceType | None = None
) -> list[RegulatoryMapping]:
    stmt = select(RegulatoryMapping)
    if guidance_type is not None:
        stmt = stmt.where(RegulatoryMapping.guidance_type == guidance_type)
    return list(db.execute(stmt).scalars().all())


def create_mapping(
    db: Session, data: RegulatoryMappingCreate, *, user: str = "admin"
) -> RegulatoryMapping:
    if get_mapping(db, data.control_key) is not None:
        raise DuplicateRegulatoryMappingError(
            f"A regulatory mapping for control_key {data.control_key!r} already exists"
        )

    mapping = RegulatoryMapping(**data.model_dump())
    db.add(mapping)
    db.flush()
    write_audit(
        db, "REGULATORY_MAPPING_UPDATED", user=user,
        detail={"control_key": mapping.control_key, "operation": "created"},
    )
    db.commit()
    db.refresh(mapping)
    return mapping


def update_mapping(
    db: Session, control_key: str, data: RegulatoryMappingUpdate, *, user: str = "admin"
) -> RegulatoryMapping:
    mapping = get_mapping(db, control_key)
    if mapping is None:
        raise RegulatoryMappingNotFoundError(f"No regulatory mapping for control_key={control_key!r}")

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(mapping, field, value)

    db.flush()
    write_audit(
        db, "REGULATORY_MAPPING_UPDATED", user=user,
        detail={"control_key": mapping.control_key, "operation": "updated", "fields": sorted(changes)},
    )
    db.commit()
    db.refresh(mapping)
    return mapping


def resolve_reference(db: Session, control_key: str) -> ResolvedReference | None:
    mapping = get_mapping(db, control_key)
    if mapping is None:
        return None
    return ResolvedReference(
        regulation_name=mapping.regulation_name,
        reference_text=mapping.reference_text,
        guidance_type=mapping.guidance_type.value,
        effective_note=mapping.effective_note,
    )
