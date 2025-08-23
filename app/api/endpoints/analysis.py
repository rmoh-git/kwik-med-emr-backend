from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.analysis_crud_service import AnalysisCrudService
from app.models.analysis import AnalysisStatusEnum
from app.schemas.analysis import (
    AnalysisUpdate,
    AnalysisResponse,
    AnalysisListResponse,
    AnalysisRequest
)
from app.services.analysis_service import analysis_service

router = APIRouter()


@router.post("/", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    try:
        created_analysis = analysis_service_crud.create_analysis(request)
        
        # Get the analysis model for background processing
        analysis_model = analysis_service_crud.analysis_repo.get_by_id(created_analysis.id)
        
        # Start analysis in background
        background_tasks.add_task(analysis_service.perform_analysis, analysis_model, db)
        
        return created_analysis
    except ValueError as e:
        if "Session not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    analysis = analysis_service_crud.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return analysis


@router.put("/{analysis_id}", response_model=AnalysisResponse)
def update_analysis(
    analysis_id: UUID,
    analysis_data: AnalysisUpdate,
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    updated_analysis = analysis_service_crud.update_analysis(analysis_id, analysis_data)
    if not updated_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return updated_analysis


@router.post("/{analysis_id}/retry", response_model=AnalysisResponse)
async def retry_analysis(
    analysis_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    try:
        reset_analysis = analysis_service_crud.retry_analysis(analysis_id)
        if not reset_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Get the analysis model for background processing
        analysis_model = analysis_service_crud.analysis_repo.get_by_id(analysis_id)
        
        # Start analysis in background
        background_tasks.add_task(analysis_service.perform_analysis, analysis_model, db)
        
        return reset_analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/session/{session_id}", response_model=AnalysisListResponse)
def get_session_analyses(
    session_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: AnalysisStatusEnum = Query(default=None),
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    try:
        return analysis_service_crud.get_session_analyses(session_id, status, limit, offset)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/patient/{patient_id}", response_model=AnalysisListResponse)
def get_patient_analyses(
    patient_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: AnalysisStatusEnum = Query(default=None),
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    return analysis_service_crud.get_patient_analyses(patient_id, status, limit, offset)


@router.get("/", response_model=AnalysisListResponse)
def list_analyses(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: AnalysisStatusEnum = Query(default=None),
    db: Session = Depends(get_database)
):
    analysis_service_crud = AnalysisCrudService(db)
    return analysis_service_crud.list_analyses(status, limit, offset)