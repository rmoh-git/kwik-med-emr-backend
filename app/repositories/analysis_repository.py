from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base import BaseRepository
from app.models.analysis import Analysis, AnalysisStatusEnum, AnalysisTypeEnum
from app.models.session import Session as SessionModel


class AnalysisRepository(BaseRepository[Analysis]):
    def __init__(self, db: Session):
        super().__init__(db, Analysis)
    
    def get_by_session_id(self, session_id: UUID, skip: int = 0, limit: int = 10) -> List[Analysis]:
        """Get analyses for a specific session"""
        return (
            self.db.query(Analysis)
            .filter(Analysis.session_id == session_id)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_session_id(self, session_id: UUID) -> int:
        """Count analyses for a specific session"""
        return (
            self.db.query(Analysis)
            .filter(Analysis.session_id == session_id)
            .count()
        )
    
    def get_by_patient_id(self, patient_id: UUID, skip: int = 0, limit: int = 10) -> List[Analysis]:
        """Get analyses for all sessions of a specific patient"""
        return (
            self.db.query(Analysis)
            .join(SessionModel)
            .filter(SessionModel.patient_id == patient_id)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_patient_id(self, patient_id: UUID) -> int:
        """Count analyses for a specific patient"""
        return (
            self.db.query(Analysis)
            .join(SessionModel)
            .filter(SessionModel.patient_id == patient_id)
            .count()
        )
    
    def get_by_status(self, status: AnalysisStatusEnum, skip: int = 0, limit: int = 10) -> List[Analysis]:
        """Get analyses by status"""
        return (
            self.db.query(Analysis)
            .filter(Analysis.status == status)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_session_and_status(
        self, 
        session_id: UUID, 
        status: AnalysisStatusEnum,
        skip: int = 0,
        limit: int = 10
    ) -> List[Analysis]:
        """Get analyses by session and status"""
        return (
            self.db.query(Analysis)
            .filter(
                Analysis.session_id == session_id,
                Analysis.status == status
            )
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_type(
        self, 
        analysis_type: AnalysisTypeEnum, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[Analysis]:
        """Get analyses by type"""
        return (
            self.db.query(Analysis)
            .filter(Analysis.analysis_type == analysis_type)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_completed_analyses_by_patient(self, patient_id: UUID) -> List[Analysis]:
        """Get completed analyses for patient history"""
        return (
            self.db.query(Analysis)
            .join(SessionModel)
            .filter(
                SessionModel.patient_id == patient_id,
                Analysis.status == AnalysisStatusEnum.COMPLETED
            )
            .order_by(Analysis.created_at.desc())
            .all()
        )