from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class SessionStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    practitioner_name = Column(String(100), nullable=False)
    practitioner_id = Column(String(50), nullable=True, index=True)
    visit_type = Column(String(100), nullable=False)
    chief_complaint = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(SessionStatusEnum), default=SessionStatusEnum.ACTIVE, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    patient = relationship("Patient", backref="sessions")
    recordings = relationship("Recording", back_populates="session")
    analyses = relationship("Analysis", back_populates="session")