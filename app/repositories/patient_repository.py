from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.repositories.base import BaseRepository
from app.models.patient import Patient


class PatientRepository(BaseRepository[Patient]):
    def __init__(self, db: Session):
        super().__init__(db, Patient)
    
    def search_patients(self, query: str, skip: int = 0, limit: int = 10) -> List[Patient]:
        """Search patients by name, phone, or medical record number"""
        search_filter = or_(
            Patient.first_name.ilike(f"%{query}%"),
            Patient.last_name.ilike(f"%{query}%"),
            Patient.phone.ilike(f"%{query}%"),
            Patient.medical_record_number.ilike(f"%{query}%")
        )
        
        return (
            self.db.query(Patient)
            .filter(search_filter)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_search_results(self, query: str) -> int:
        """Count search results for pagination"""
        search_filter = or_(
            Patient.first_name.ilike(f"%{query}%"),
            Patient.last_name.ilike(f"%{query}%"),
            Patient.phone.ilike(f"%{query}%"),
            Patient.medical_record_number.ilike(f"%{query}%")
        )
        
        return self.db.query(Patient).filter(search_filter).count()
    
    def get_by_mrn(self, mrn: str) -> Optional[Patient]:
        """Get patient by medical record number"""
        return (
            self.db.query(Patient)
            .filter(Patient.medical_record_number == mrn)
            .first()
        )
    
    def get_by_email(self, email: str) -> Optional[Patient]:
        """Get patient by email"""
        return (
            self.db.query(Patient)
            .filter(Patient.email == email)
            .first()
        )
    
    def get_by_phone(self, phone: str) -> Optional[Patient]:
        """Get patient by phone number"""
        return (
            self.db.query(Patient)
            .filter(Patient.phone == phone)
            .first()
        )