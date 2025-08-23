from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as DBSession

from app.repositories.base import BaseRepository
from app.models.session import Session, SessionStatusEnum


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: DBSession):
        super().__init__(db, Session)
    
    def get_by_patient_id(self, patient_id: UUID, skip: int = 0, limit: int = 10) -> List[Session]:
        """Get sessions for a specific patient"""
        return (
            self.db.query(Session)
            .filter(Session.patient_id == patient_id)
            .order_by(Session.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_patient_id(self, patient_id: UUID) -> int:
        """Count sessions for a specific patient"""
        return (
            self.db.query(Session)
            .filter(Session.patient_id == patient_id)
            .count()
        )
    
    def get_by_status(self, status: SessionStatusEnum, skip: int = 0, limit: int = 10) -> List[Session]:
        """Get sessions by status"""
        return (
            self.db.query(Session)
            .filter(Session.status == status)
            .order_by(Session.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active_session_by_patient(self, patient_id: UUID) -> Optional[Session]:
        """Get active session for a patient"""
        return (
            self.db.query(Session)
            .filter(
                Session.patient_id == patient_id,
                Session.status == SessionStatusEnum.ACTIVE
            )
            .first()
        )
    
    def get_patient_sessions_by_status(
        self, 
        patient_id: UUID, 
        status: SessionStatusEnum, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[Session]:
        """Get patient sessions filtered by status"""
        return (
            self.db.query(Session)
            .filter(
                Session.patient_id == patient_id,
                Session.status == status
            )
            .order_by(Session.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_patient_sessions_by_status(self, patient_id: UUID, status: SessionStatusEnum) -> int:
        """Count patient sessions by status"""
        return (
            self.db.query(Session)
            .filter(
                Session.patient_id == patient_id,
                Session.status == status
            )
            .count()
        )