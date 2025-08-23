from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.session_service import SessionService
from app.models.session import SessionStatusEnum
from app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse
)

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    try:
        return session_service.create_session(session_data)
    except ValueError as e:
        if "Patient not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: UUID,
    session_data: SessionUpdate,
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    try:
        updated_session = session_service.update_session(session_id, session_data)
        if not updated_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return updated_session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: UUID,
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    try:
        ended_session = session_service.end_session(session_id)
        if not ended_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return ended_session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/patient/{patient_id}", response_model=SessionListResponse)
def get_patient_sessions(
    patient_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: SessionStatusEnum = Query(default=None),
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    try:
        return session_service.get_patient_sessions(patient_id, status, limit, offset)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: SessionStatusEnum = Query(default=None),
    db: Session = Depends(get_database)
):
    session_service = SessionService(db)
    return session_service.list_sessions(status, limit, offset)