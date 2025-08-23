from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey, Float, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class AnalysisStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTypeEnum(str, enum.Enum):
    DIAGNOSIS_ASSISTANCE = "diagnosis_assistance"
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    FOLLOW_UP_PLANNING = "follow_up_planning"
    GENERAL_ANALYSIS = "general_analysis"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    analysis_type = Column(Enum(AnalysisTypeEnum), nullable=False)
    prompt_context = Column(Text, nullable=True)
    status = Column(Enum(AnalysisStatusEnum), default=AnalysisStatusEnum.PENDING, nullable=False)
    result = Column(JSON, nullable=True)  # Store analysis result as JSON
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="analyses")