from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.recording_repository import RecordingRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.recording import (
    RecordingCreate, 
    RecordingUpdate, 
    RecordingResponse,
    RecordingStartRequest,
    RecordingStopRequest
)
from app.models.recording import RecordingStatusEnum
from app.models.session import SessionStatusEnum
from app.services.audio_service import audio_service


class RecordingService:
    def __init__(self, db: Session):
        self.db = db
        self.recording_repo = RecordingRepository(db)
        self.session_repo = SessionRepository(db)
    
    def start_recording(self, request: RecordingStartRequest) -> RecordingResponse:
        """Start a new recording for a session"""
        # Verify session exists and is active
        session = self.session_repo.get_by_id(request.session_id)
        if not session:
            raise ValueError("Session not found")
        
        if session.status != SessionStatusEnum.ACTIVE:
            raise ValueError("Session is not active")
        
        # Check if there's already an active recording for this session
        active_recording = self.recording_repo.get_active_recording_by_session(request.session_id)
        if active_recording:
            raise ValueError("Session already has an active recording")
        
        # Create new recording record
        recording_data = RecordingCreate(
            session_id=request.session_id,
            file_name=f"recording_{session.id}_{session.created_at.strftime('%Y%m%d_%H%M%S')}.wav",
            file_path=""  # Will be set when file is uploaded
        )
        
        recording_dict = recording_data.model_dump()
        recording = self.recording_repo.create(recording_dict)
        return RecordingResponse.model_validate(recording)
    
    def stop_recording(self, request: RecordingStopRequest) -> Optional[RecordingResponse]:
        """Stop an active recording"""
        recording = self.recording_repo.get_by_id(request.recording_id)
        if not recording:
            return None
        
        if recording.status != RecordingStatusEnum.RECORDING:
            raise ValueError("Recording is not active")
        
        # Update recording status
        updated_recording = self.recording_repo.update(
            request.recording_id, 
            {"status": RecordingStatusEnum.STOPPED}
        )
        
        return RecordingResponse.model_validate(updated_recording)
    
    def get_recording(self, recording_id: UUID) -> Optional[RecordingResponse]:
        """Get a recording by ID"""
        recording = self.recording_repo.get_by_id(recording_id)
        if not recording:
            return None
        return RecordingResponse.model_validate(recording)
    
    def update_recording(self, recording_id: UUID, recording_data: RecordingUpdate) -> Optional[RecordingResponse]:
        """Update a recording"""
        if not self.recording_repo.exists(recording_id):
            return None
        
        update_dict = recording_data.model_dump(exclude_unset=True)
        updated_recording = self.recording_repo.update(recording_id, update_dict)
        
        if not updated_recording:
            return None
        
        return RecordingResponse.model_validate(updated_recording)
    
    def get_session_recordings(self, session_id: UUID) -> List[RecordingResponse]:
        """Get all recordings for a session"""
        # Verify session exists
        if not self.session_repo.exists(session_id):
            raise ValueError("Session not found")
        
        recordings = self.recording_repo.get_by_session_id(session_id)
        return [RecordingResponse.model_validate(r) for r in recordings]
    
    def upload_audio_file(
        self, 
        recording_id: UUID, 
        file_content: bytes, 
        filename: str
    ) -> Optional[RecordingResponse]:
        """Upload audio file for a recording"""
        recording = self.recording_repo.get_by_id(recording_id)
        if not recording:
            return None
        
        if recording.status not in [RecordingStatusEnum.RECORDING, RecordingStatusEnum.STOPPED]:
            raise ValueError("Recording is not in a valid state for upload")
        
        # Validate file type
        if not audio_service.validate_audio_file(filename):
            raise ValueError(f"Invalid file type. Allowed types: {', '.join(audio_service.settings.ALLOWED_AUDIO_EXTENSIONS)}")
        
        # Check file size
        if len(file_content) > audio_service.settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {audio_service.settings.MAX_FILE_SIZE} bytes")
        
        # This would be handled by audio_service.save_audio_file in the endpoint
        # Return the recording for now
        return RecordingResponse.model_validate(recording)
    
    def initiate_transcription(self, recording_id: UUID) -> Optional[RecordingResponse]:
        """Initiate transcription for a recording"""
        recording = self.recording_repo.get_by_id(recording_id)
        if not recording:
            return None
        
        if recording.status not in [RecordingStatusEnum.STOPPED, RecordingStatusEnum.FAILED]:
            raise ValueError("Recording is not ready for transcription")
        
        if not recording.file_path or not recording.file_name:
            raise ValueError("No audio file associated with this recording")
        
        # Update status to processing
        updated_recording = self.recording_repo.update(
            recording_id, 
            {"status": RecordingStatusEnum.PROCESSING}
        )
        
        return RecordingResponse.model_validate(updated_recording)
    
    def get_recordings_with_transcripts(self, session_id: UUID) -> List[RecordingResponse]:
        """Get recordings that have transcripts for a session"""
        recordings = self.recording_repo.get_recordings_with_transcripts(session_id)
        return [RecordingResponse.model_validate(r) for r in recordings]
    
    def recording_exists(self, recording_id: UUID) -> bool:
        """Check if a recording exists"""
        return self.recording_repo.exists(recording_id)