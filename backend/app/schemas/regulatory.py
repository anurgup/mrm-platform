from pydantic import BaseModel, ConfigDict

from app.models.enums import GuidanceType


class RegulatoryMappingBase(BaseModel):
    control_key: str
    regulation_name: str
    reference_text: str
    guidance_type: GuidanceType
    effective_note: str | None = None


class RegulatoryMappingCreate(RegulatoryMappingBase):
    pass


class RegulatoryMappingUpdate(BaseModel):
    """Partial update. `control_key` is deliberately absent — it's the stable
    identifier the control engine and findings key off of."""

    regulation_name: str | None = None
    reference_text: str | None = None
    guidance_type: GuidanceType | None = None
    effective_note: str | None = None


class RegulatoryMappingOut(RegulatoryMappingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
