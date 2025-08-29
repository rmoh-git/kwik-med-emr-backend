from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey, Float, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class RecordingStatusEnum(str, enum.Enum):
    RECORDING = "RECORDING"
    STOPPED = "STOPPED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LanguageEnum(str, enum.Enum):
    ENGLISH = "ENGLISH"
    FRENCH = "FRENCH"
    SWAHILI = "SWAHILI"
    KINYARWANDA = "KINYARWANDA"


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    language = Column(Enum(LanguageEnum), default=LanguageEnum.ENGLISH, nullable=False)
    status = Column(Enum(RecordingStatusEnum), default=RecordingStatusEnum.RECORDING, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)  # Store transcript segments as JSON
    processing_error = Column(Text, nullable=True)
    additional_data = Column(JSON, nullable=True)  # Store additional data like dual-language info
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="recordings")