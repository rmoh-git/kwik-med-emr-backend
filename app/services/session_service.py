from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.session_repository import SessionRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
from app.models.session import SessionStatusEnum


class SessionService:
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.patient_repo = PatientRepository(db)
        self.practitioner_repo = PractitionerRepository(db)
    
    def create_session(self, session_data: SessionCreate) -> SessionResponse:
        """Create a new session"""
        # Verify patient exists
        if not self.patient_repo.exists(session_data.patient_id):
            raise ValueError("Patient not found")
        
        # Verify practitioner exists and get practitioner info
        practitioner = self.practitioner_repo.get_by_id(session_data.practitioner_id)
        if not practitioner:
            raise ValueError("Practitioner not found")
        
        # Check if patient has an active session
        active_session = self.session_repo.get_active_session_by_patient(session_data.patient_id)
        if active_session:
            raise ValueError("Patient already has an active session")
        
        # Create the session with inferred practitioner information
        session_dict = session_data.model_dump()
        session_dict["practitioner_name"] = f"{practitioner.first_name} {practitioner.last_name}"
        session_dict["practitioner_id"] = str(practitioner.id)
        
        session = self.session_repo.create(session_dict)
        return SessionResponse.model_validate(session)
    
    def get_session(self, session_id: UUID) -> Optional[SessionResponse]:
        """Get a session by ID"""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            return None
        return SessionResponse.model_validate(session)
    
    def update_session(self, session_id: UUID, session_data: SessionUpdate) -> Optional[SessionResponse]:
        """Update a session"""
        if not self.session_repo.exists(session_id):
            return None
        
        update_dict = session_data.model_dump(exclude_unset=True)
        
        # If status is being changed to completed or cancelled, set ended_at
        if 'status' in update_dict and update_dict['status'] in [SessionStatusEnum.COMPLETED, SessionStatusEnum.CANCELLED]:
            update_dict['ended_at'] = datetime.utcnow()
        
        updated_session = self.session_repo.update(session_id, update_dict)
        if not updated_session:
            return None
        
        return SessionResponse.model_validate(updated_session)
    
    def end_session(self, session_id: UUID) -> Optional[SessionResponse]:
        """End an active session"""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            return None
        
        if session.status != SessionStatusEnum.ACTIVE:
            raise ValueError("Session is not active")
        
        update_dict = {
            'status': SessionStatusEnum.COMPLETED,
            'ended_at': datetime.utcnow()
        }
        
        updated_session = self.session_repo.update(session_id, update_dict)
        return SessionResponse.model_validate(updated_session)
    
    def get_patient_sessions(
        self, 
        patient_id: UUID, 
        status: Optional[SessionStatusEnum] = None,
        limit: int = 10, 
        offset: int = 0
    ) -> SessionListResponse:
        """Get sessions for a specific patient"""
        # Verify patient exists
        if not self.patient_repo.exists(patient_id):
            raise ValueError("Patient not found")
        
        if status:
            sessions = self.session_repo.get_patient_sessions_by_status(patient_id, status, offset, limit)
            total = self.session_repo.count_patient_sessions_by_status(patient_id, status)
        else:
            sessions = self.session_repo.get_by_patient_id(patient_id, offset, limit)
            total = self.session_repo.count_by_patient_id(patient_id)
        
        session_responses = [SessionResponse.model_validate(s) for s in sessions]
        
        return SessionListResponse(
            sessions=session_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def list_sessions(
        self,
        status: Optional[SessionStatusEnum] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SessionListResponse:
        """List all sessions with optional status filter"""
        if status:
            sessions = self.session_repo.get_by_status(status, offset, limit)
            # Note: would need to add count_by_status method to repository
            total = len(sessions)  # Simplified for now
        else:
            sessions = self.session_repo.get_all(offset, limit)
            total = self.session_repo.count()
        
        session_responses = [SessionResponse.model_validate(s) for s in sessions]
        
        return SessionListResponse(
            sessions=session_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def session_exists(self, session_id: UUID) -> bool:
        """Check if a session exists"""
        return self.session_repo.exists(session_id)
    
    def get_active_session_for_patient(self, patient_id: UUID) -> Optional[SessionResponse]:
        """Get active session for a patient"""
        session = self.session_repo.get_active_session_by_patient(patient_id)
        if not session:
            return None
        return SessionResponse.model_validate(session)