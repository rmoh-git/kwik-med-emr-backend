from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class RecordingStatusEnum(str, Enum):
    RECORDING = "RECORDING"
    STOPPED = "STOPPED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SpeakerEnum(str, Enum):
    PRACTITIONER = "practitioner"
    PATIENT = "patient"
    UNKNOWN = "unknown"


class TranscriptSegment(BaseModel):
    text: str
    speaker: SpeakerEnum
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class RecordingBase(BaseModel):
    session_id: UUID
    file_name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)


class RecordingCreate(RecordingBase):
    pass


class RecordingUpdate(BaseModel):
    status: Optional[RecordingStatusEnum] = None
    transcript: Optional[str] = None
    transcript_segments: Optional[List[TranscriptSegment]] = None
    processing_error: Optional[str] = None


class RecordingResponse(RecordingBase):
    id: UUID
    status: RecordingStatusEnum
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    transcript: Optional[str] = None
    transcript_segments: Optional[List[TranscriptSegment]] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecordingStartRequest(BaseModel):
    session_id: UUID


class RecordingStopRequest(BaseModel):
    recording_id: UUID