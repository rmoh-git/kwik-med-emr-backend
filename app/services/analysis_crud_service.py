from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.recording_repository import RecordingRepository
from app.schemas.analysis import (
    AnalysisCreate, 
    AnalysisUpdate, 
    AnalysisResponse,
    AnalysisListResponse,
    AnalysisRequest
)
from app.models.analysis import AnalysisStatusEnum


class AnalysisCrudService:
    def __init__(self, db: Session):
        self.db = db
        self.analysis_repo = AnalysisRepository(db)
        self.session_repo = SessionRepository(db)
        self.recording_repo = RecordingRepository(db)
    
    def create_analysis(self, request: AnalysisRequest) -> AnalysisResponse:
        """Create a new analysis"""
        # Verify session exists
        if not self.session_repo.exists(request.session_id):
            raise ValueError("Session not found")
        
        # Check if session has a completed recording with transcript
        recordings = self.recording_repo.get_recordings_with_transcripts(request.session_id)
        if not recordings:
            raise ValueError("Session must have a completed recording with transcript before analysis")
        
        # Create analysis record
        analysis_data = AnalysisCreate(
            session_id=request.session_id,
            analysis_type=request.analysis_type,
            prompt_context=request.custom_prompt
        )
        
        analysis_dict = analysis_data.model_dump()
        analysis = self.analysis_repo.create(analysis_dict)
        return AnalysisResponse.model_validate(analysis)
    
    def get_analysis(self, analysis_id: UUID) -> Optional[AnalysisResponse]:
        """Get an analysis by ID"""
        analysis = self.analysis_repo.get_by_id(analysis_id)
        if not analysis:
            return None
        return AnalysisResponse.model_validate(analysis)
    
    def update_analysis(self, analysis_id: UUID, analysis_data: AnalysisUpdate) -> Optional[AnalysisResponse]:
        """Update an analysis"""
        if not self.analysis_repo.exists(analysis_id):
            return None
        
        update_dict = analysis_data.model_dump(exclude_unset=True)
        updated_analysis = self.analysis_repo.update(analysis_id, update_dict)
        
        if not updated_analysis:
            return None
        
        return AnalysisResponse.model_validate(updated_analysis)
    
    def retry_analysis(self, analysis_id: UUID) -> Optional[AnalysisResponse]:
        """Retry a failed or completed analysis"""
        analysis = self.analysis_repo.get_by_id(analysis_id)
        if not analysis:
            return None
        
        if analysis.status not in [AnalysisStatusEnum.FAILED, AnalysisStatusEnum.COMPLETED]:
            raise ValueError("Analysis can only be retried if it failed or completed")
        
        # Reset analysis status
        update_dict = {
            'status': AnalysisStatusEnum.PENDING,
            'result': None,
            'error_message': None,
            'tokens_used': None,
            'processing_time_seconds': None
        }
        
        updated_analysis = self.analysis_repo.update(analysis_id, update_dict)
        return AnalysisResponse.model_validate(updated_analysis)
    
    def get_session_analyses(
        self, 
        session_id: UUID,
        status: Optional[AnalysisStatusEnum] = None,
        limit: int = 10,
        offset: int = 0
    ) -> AnalysisListResponse:
        """Get analyses for a specific session"""
        # Verify session exists
        if not self.session_repo.exists(session_id):
            raise ValueError("Session not found")
        
        if status:
            analyses = self.analysis_repo.get_by_session_and_status(session_id, status, offset, limit)
            # Note: Would need to add count method for session + status combination
            total = len(analyses)  # Simplified for now
        else:
            analyses = self.analysis_repo.get_by_session_id(session_id, offset, limit)
            total = self.analysis_repo.count_by_session_id(session_id)
        
        analysis_responses = [AnalysisResponse.model_validate(a) for a in analyses]
        
        return AnalysisListResponse(
            analyses=analysis_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def get_patient_analyses(
        self,
        patient_id: UUID,
        status: Optional[AnalysisStatusEnum] = None,
        limit: int = 10,
        offset: int = 0
    ) -> AnalysisListResponse:
        """Get analyses for all sessions of a specific patient"""
        # Note: We don't need to verify patient exists since the query will return empty if not
        
        if status:
            # For simplicity, get all patient analyses and filter by status
            # In production, you'd want a more efficient repository method
            all_analyses = self.analysis_repo.get_by_patient_id(patient_id, 0, 1000)  # Large limit
            analyses = [a for a in all_analyses if a.status == status][offset:offset+limit]
            total = len([a for a in all_analyses if a.status == status])
        else:
            analyses = self.analysis_repo.get_by_patient_id(patient_id, offset, limit)
            total = self.analysis_repo.count_by_patient_id(patient_id)
        
        analysis_responses = [AnalysisResponse.model_validate(a) for a in analyses]
        
        return AnalysisListResponse(
            analyses=analysis_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def list_analyses(
        self,
        status: Optional[AnalysisStatusEnum] = None,
        limit: int = 10,
        offset: int = 0
    ) -> AnalysisListResponse:
        """List all analyses with optional status filter"""
        if status:
            analyses = self.analysis_repo.get_by_status(status, offset, limit)
            # Note: Would need to add count_by_status method to repository
            total = len(analyses)  # Simplified for now
        else:
            analyses = self.analysis_repo.get_all(offset, limit)
            total = self.analysis_repo.count()
        
        analysis_responses = [AnalysisResponse.model_validate(a) for a in analyses]
        
        return AnalysisListResponse(
            analyses=analysis_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def analysis_exists(self, analysis_id: UUID) -> bool:
        """Check if an analysis exists"""
        return self.analysis_repo.exists(analysis_id)