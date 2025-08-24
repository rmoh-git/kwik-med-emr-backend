from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatusEnum(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SessionBase(BaseModel):
    patient_id: UUID
    practitioner_name: str = Field(..., min_length=1, max_length=100)
    practitioner_id: Optional[str] = Field(None, max_length=50)
    visit_type: str = Field(..., min_length=1, max_length=100)
    chief_complaint: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class SessionCreate(BaseModel):
    patient_id: UUID
    practitioner_id: UUID
    visit_type: Optional[str] = Field(default="consultation", max_length=100)
    chief_complaint: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    practitioner_name: Optional[str] = Field(None, min_length=1, max_length=100)
    practitioner_id: Optional[str] = Field(None, max_length=50)
    visit_type: Optional[str] = Field(None, min_length=1, max_length=100)
    chief_complaint: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    status: Optional[SessionStatusEnum] = None


class SessionResponse(SessionBase):
    id: UUID
    status: SessionStatusEnum
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
    limit: int
    offset: int