from typing import TypeVar, Generic, List, Optional, Type, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination, ordered from most recent to oldest"""
        query = self.db.query(self.model)
        
        # Order by created_at if available, otherwise by updated_at, otherwise by id
        if hasattr(self.model, 'created_at'):
            query = query.order_by(self.model.created_at.desc())
        elif hasattr(self.model, 'updated_at'):
            query = query.order_by(self.model.updated_at.desc())
        elif hasattr(self.model, 'id'):
            query = query.order_by(self.model.id.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, id: UUID, update_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record by ID"""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: UUID) -> bool:
        """Delete a record by ID"""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return False
        
        self.db.delete(db_obj)
        self.db.commit()
        return True
    
    def count(self) -> int:
        """Get total count of records"""
        return self.db.query(self.model).count()
    
    def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first() is not None