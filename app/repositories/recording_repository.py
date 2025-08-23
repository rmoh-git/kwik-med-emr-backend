from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.recording import Recording, RecordingStatusEnum


class RecordingRepository(BaseRepository[Recording]):
    def __init__(self, db: Session):
        super().__init__(db, Recording)
    
    def get_by_session_id(self, session_id: UUID) -> List[Recording]:
        """Get all recordings for a session"""
        return (
            self.db.query(Recording)
            .filter(Recording.session_id == session_id)
            .order_by(Recording.created_at.desc())
            .all()
        )
    
    def get_by_status(self, status: RecordingStatusEnum) -> List[Recording]:
        """Get recordings by status"""
        return (
            self.db.query(Recording)
            .filter(Recording.status == status)
            .order_by(Recording.created_at.desc())
            .all()
        )
    
    def get_active_recording_by_session(self, session_id: UUID) -> Optional[Recording]:
        """Get active recording for a session"""
        return (
            self.db.query(Recording)
            .filter(
                Recording.session_id == session_id,
                Recording.status == RecordingStatusEnum.RECORDING
            )
            .first()
        )
    
    def get_latest_by_session(self, session_id: UUID) -> Optional[Recording]:
        """Get the most recent recording for a session"""
        return (
            self.db.query(Recording)
            .filter(Recording.session_id == session_id)
            .order_by(Recording.created_at.desc())
            .first()
        )
    
    def get_completed_recordings_by_session(self, session_id: UUID) -> List[Recording]:
        """Get completed recordings for a session"""
        return (
            self.db.query(Recording)
            .filter(
                Recording.session_id == session_id,
                Recording.status == RecordingStatusEnum.COMPLETED
            )
            .order_by(Recording.created_at.desc())
            .all()
        )
    
    def get_recordings_with_transcripts(self, session_id: UUID) -> List[Recording]:
        """Get recordings that have transcripts"""
        return (
            self.db.query(Recording)
            .filter(
                Recording.session_id == session_id,
                Recording.transcript.isnot(None),
                Recording.transcript != ""
            )
            .order_by(Recording.created_at.desc())
            .all()
        )