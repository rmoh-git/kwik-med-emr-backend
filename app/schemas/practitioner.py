from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SpecialtyEnum(str, Enum):
    GENERAL_PRACTICE = "general_practice"
    CARDIOLOGY = "cardiology"
    NEUROLOGY = "neurology"
    PSYCHIATRY = "psychiatry"
    PULMONOLOGY = "pulmonology"
    ENDOCRINOLOGY = "endocrinology"
    ONCOLOGY = "oncology"
    OTHER = "other"


class PractitionerBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    license_number: str = Field(..., max_length=50)
    specialty: SpecialtyEnum
    is_active: bool = Field(default=True)


class PractitionerCreate(PractitionerBase):
    pass


class PractitionerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    license_number: Optional[str] = Field(None, max_length=50)
    specialty: Optional[SpecialtyEnum] = None
    is_active: Optional[bool] = None


class PractitionerResponse(PractitionerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PractitionerSearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="Search by name, email, or license number")
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PractitionerSearchResponse(BaseModel):
    practitioners: List[PractitionerResponse]
    total: int
    limit: int
    offset: int