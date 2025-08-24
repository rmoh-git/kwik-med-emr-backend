from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class SpecialtyEnum(str, enum.Enum):
    GENERAL_PRACTICE = "general_practice"
    CARDIOLOGY = "cardiology"
    NEUROLOGY = "neurology"
    PSYCHIATRY = "psychiatry"
    PULMONOLOGY = "pulmonology"
    ENDOCRINOLOGY = "endocrinology"
    ONCOLOGY = "oncology"
    OTHER = "other"


class Practitioner(Base):
    __tablename__ = "practitioners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    license_number = Column(String(50), nullable=False, unique=True, index=True)
    specialty = Column(Enum(SpecialtyEnum), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)