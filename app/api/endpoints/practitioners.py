from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.practitioner_service import PractitionerService
from app.schemas.practitioner import (
    PractitionerCreate,
    PractitionerUpdate,
    PractitionerResponse,
    PractitionerSearchResponse
)

router = APIRouter()


@router.post("/", response_model=PractitionerResponse, status_code=status.HTTP_201_CREATED)
def create_practitioner(
    practitioner_data: PractitionerCreate,
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    try:
        return practitioner_service.create_practitioner(practitioner_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/search", response_model=PractitionerSearchResponse)
def search_practitioners(
    query: str = Query(..., min_length=1, max_length=100, description="Search by name, email, or license number"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    return practitioner_service.search_practitioners(query, limit, offset)


@router.get("/{practitioner_id}", response_model=PractitionerResponse)
def get_practitioner(
    practitioner_id: UUID,
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    practitioner = practitioner_service.get_practitioner(practitioner_id)
    if not practitioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practitioner not found"
        )
    
    return practitioner


@router.put("/{practitioner_id}", response_model=PractitionerResponse)
def update_practitioner(
    practitioner_id: UUID,
    practitioner_data: PractitionerUpdate,
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    try:
        updated_practitioner = practitioner_service.update_practitioner(practitioner_id, practitioner_data)
        if not updated_practitioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Practitioner not found"
            )
        return updated_practitioner
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[PractitionerResponse])
def list_practitioners(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=True, description="Show only active practitioners"),
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    return practitioner_service.list_practitioners(limit, offset, active_only)


@router.delete("/{practitioner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_practitioner(
    practitioner_id: UUID,
    db: Session = Depends(get_database)
):
    practitioner_service = PractitionerService(db)
    success = practitioner_service.delete_practitioner(practitioner_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practitioner not found"
        )