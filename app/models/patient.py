from sqlalchemy import Column, String, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    address = Column(Text, nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Insurance and ID information
    national_id = Column(String(20), nullable=True, index=True)  # National ID/SSN
    insurance_provider = Column(String(100), nullable=True)
    insurance_policy_number = Column(String(50), nullable=True)
    insurance_group_number = Column(String(50), nullable=True)
    
    # MRN now uses patient UUID directly
    @property
    def medical_record_number(self):
        return str(self.id)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)