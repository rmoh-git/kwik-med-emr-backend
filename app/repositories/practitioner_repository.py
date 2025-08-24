from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.repositories.base import BaseRepository
from app.models.practitioner import Practitioner


class PractitionerRepository(BaseRepository[Practitioner]):
    def __init__(self, db: Session):
        super().__init__(db, Practitioner)
    
    def search_practitioners(self, query: str, skip: int = 0, limit: int = 10) -> List[Practitioner]:
        """Search practitioners by name, email, or license number"""
        search_filter = or_(
            Practitioner.first_name.ilike(f"%{query}%"),
            Practitioner.last_name.ilike(f"%{query}%"),
            Practitioner.email.ilike(f"%{query}%"),
            Practitioner.license_number.ilike(f"%{query}%")
        )
        
        return (
            self.db.query(Practitioner)
            .filter(search_filter)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_search_results(self, query: str) -> int:
        """Count search results for pagination"""
        search_filter = or_(
            Practitioner.first_name.ilike(f"%{query}%"),
            Practitioner.last_name.ilike(f"%{query}%"),
            Practitioner.email.ilike(f"%{query}%"),
            Practitioner.license_number.ilike(f"%{query}%")
        )
        
        return self.db.query(Practitioner).filter(search_filter).count()
    
    def get_by_email(self, email: str) -> Optional[Practitioner]:
        """Get practitioner by email"""
        return (
            self.db.query(Practitioner)
            .filter(Practitioner.email == email)
            .first()
        )
    
    def get_by_license(self, license_number: str) -> Optional[Practitioner]:
        """Get practitioner by license number"""
        return (
            self.db.query(Practitioner)
            .filter(Practitioner.license_number == license_number)
            .first()
        )
    
    def get_active_practitioners(self, skip: int = 0, limit: int = 100) -> List[Practitioner]:
        """Get all active practitioners"""
        return (
            self.db.query(Practitioner)
            .filter(Practitioner.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )