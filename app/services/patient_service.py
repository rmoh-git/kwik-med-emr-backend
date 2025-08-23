from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientSearchResponse
from app.models.patient import Patient


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.patient_repo = PatientRepository(db)
    
    def create_patient(self, patient_data: PatientCreate) -> PatientResponse:
        """Create a new patient"""
        # Exclude MRN from input data as it will be auto-generated
        patient_dict = patient_data.model_dump(exclude={'medical_record_number'})
        
        # Create the patient
        patient = self.patient_repo.create(patient_dict)
        return PatientResponse.model_validate(patient)
    
    def get_patient(self, patient_id: UUID) -> Optional[PatientResponse]:
        """Get a patient by ID"""
        patient = self.patient_repo.get_by_id(patient_id)
        if not patient:
            return None
        return PatientResponse.model_validate(patient)
    
    def update_patient(self, patient_id: UUID, patient_data: PatientUpdate) -> Optional[PatientResponse]:
        """Update a patient"""
        # Check if patient exists
        if not self.patient_repo.exists(patient_id):
            return None
        
        # Check if MRN is being updated and already exists
        update_dict = patient_data.model_dump(exclude_unset=True)
        if 'medical_record_number' in update_dict:
            existing_patient = self.patient_repo.get_by_mrn(update_dict['medical_record_number'])
            if existing_patient and existing_patient.id != patient_id:
                raise ValueError("Patient with this medical record number already exists")
        
        # Update the patient
        updated_patient = self.patient_repo.update(patient_id, update_dict)
        if not updated_patient:
            return None
        
        return PatientResponse.model_validate(updated_patient)
    
    def search_patients(self, query: str, limit: int = 10, offset: int = 0) -> PatientSearchResponse:
        """Search patients by name, phone, or MRN"""
        patients = self.patient_repo.search_patients(query, offset, limit)
        total = self.patient_repo.count_search_results(query)
        
        patient_responses = [PatientResponse.model_validate(p) for p in patients]
        
        return PatientSearchResponse(
            patients=patient_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def list_patients(self, limit: int = 10, offset: int = 0) -> List[PatientResponse]:
        """List patients with pagination"""
        patients = self.patient_repo.get_all(offset, limit)
        return [PatientResponse.model_validate(p) for p in patients]
    
    def delete_patient(self, patient_id: UUID) -> bool:
        """Delete a patient"""
        return self.patient_repo.delete(patient_id)
    
    def patient_exists(self, patient_id: UUID) -> bool:
        """Check if a patient exists"""
        return self.patient_repo.exists(patient_id)
    
    def get_patient_by_mrn(self, mrn: str) -> Optional[PatientResponse]:
        """Get patient by medical record number"""
        patient = self.patient_repo.get_by_mrn(mrn)
        if not patient:
            return None
        return PatientResponse.model_validate(patient)