from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.practitioner_repository import PractitionerRepository
from app.schemas.practitioner import PractitionerCreate, PractitionerUpdate, PractitionerResponse, PractitionerSearchResponse
from app.models.practitioner import Practitioner


class PractitionerService:
    def __init__(self, db: Session):
        self.db = db
        self.practitioner_repo = PractitionerRepository(db)
    
    def create_practitioner(self, practitioner_data: PractitionerCreate) -> PractitionerResponse:
        """Create a new practitioner"""
        # Check if email already exists
        existing_email = self.practitioner_repo.get_by_email(practitioner_data.email)
        if existing_email:
            raise ValueError("Practitioner with this email already exists")
        
        # Check if license number already exists
        existing_license = self.practitioner_repo.get_by_license(practitioner_data.license_number)
        if existing_license:
            raise ValueError("Practitioner with this license number already exists")
        
        practitioner_dict = practitioner_data.model_dump()
        practitioner = self.practitioner_repo.create(practitioner_dict)
        return PractitionerResponse.model_validate(practitioner)
    
    def get_practitioner(self, practitioner_id: UUID) -> Optional[PractitionerResponse]:
        """Get a practitioner by ID"""
        practitioner = self.practitioner_repo.get_by_id(practitioner_id)
        if not practitioner:
            return None
        return PractitionerResponse.model_validate(practitioner)
    
    def update_practitioner(self, practitioner_id: UUID, practitioner_data: PractitionerUpdate) -> Optional[PractitionerResponse]:
        """Update a practitioner"""
        if not self.practitioner_repo.exists(practitioner_id):
            return None
        
        update_dict = practitioner_data.model_dump(exclude_unset=True)
        
        # Check if email is being updated and already exists
        if 'email' in update_dict:
            existing_email = self.practitioner_repo.get_by_email(update_dict['email'])
            if existing_email and existing_email.id != practitioner_id:
                raise ValueError("Practitioner with this email already exists")
        
        # Check if license number is being updated and already exists
        if 'license_number' in update_dict:
            existing_license = self.practitioner_repo.get_by_license(update_dict['license_number'])
            if existing_license and existing_license.id != practitioner_id:
                raise ValueError("Practitioner with this license number already exists")
        
        updated_practitioner = self.practitioner_repo.update(practitioner_id, update_dict)
        if not updated_practitioner:
            return None
        
        return PractitionerResponse.model_validate(updated_practitioner)
    
    def search_practitioners(self, query: str, limit: int = 10, offset: int = 0) -> PractitionerSearchResponse:
        """Search practitioners by name, email, or license number"""
        practitioners = self.practitioner_repo.search_practitioners(query, offset, limit)
        total = self.practitioner_repo.count_search_results(query)
        
        practitioner_responses = [PractitionerResponse.model_validate(p) for p in practitioners]
        
        return PractitionerSearchResponse(
            practitioners=practitioner_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    
    def list_practitioners(self, limit: int = 10, offset: int = 0, active_only: bool = True) -> List[PractitionerResponse]:
        """List practitioners with pagination"""
        if active_only:
            practitioners = self.practitioner_repo.get_active_practitioners(offset, limit)
        else:
            practitioners = self.practitioner_repo.get_all(offset, limit)
        return [PractitionerResponse.model_validate(p) for p in practitioners]
    
    def delete_practitioner(self, practitioner_id: UUID) -> bool:
        """Delete a practitioner (soft delete by setting is_active to False)"""
        practitioner = self.practitioner_repo.get_by_id(practitioner_id)
        if not practitioner:
            return False
        
        return self.practitioner_repo.update(practitioner_id, {"is_active": False}) is not None
    
    def practitioner_exists(self, practitioner_id: UUID) -> bool:
        """Check if a practitioner exists"""
        return self.practitioner_repo.exists(practitioner_id)
    
    def get_practitioner_by_email(self, email: str) -> Optional[PractitionerResponse]:
        """Get practitioner by email"""
        practitioner = self.practitioner_repo.get_by_email(email)
        if not practitioner:
            return None
        return PractitionerResponse.model_validate(practitioner)