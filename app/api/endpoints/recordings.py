from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.recording_service import RecordingService
from app.schemas.recording import (
    RecordingResponse,
    RecordingStartRequest,
    RecordingStopRequest
)
from app.services.audio_service import audio_service
from app.core.config import settings

router = APIRouter()


@router.post("/start", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
def start_recording(
    request: RecordingStartRequest,
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    try:
        return recording_service.start_recording(request)
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


@router.post("/stop", response_model=RecordingResponse)
def stop_recording(
    request: RecordingStopRequest,
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    try:
        stopped_recording = recording_service.stop_recording(request)
        if not stopped_recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        return stopped_recording
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{recording_id}/upload", response_model=RecordingResponse)
async def upload_audio_file(
    recording_id: UUID,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    
    # Check file size first
    file_content = await audio_file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Validate using service (will check existence and state)
    try:
        recording_service.upload_audio_file(recording_id, file_content, audio_file.filename)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    try:
        # Save file
        file_path = await audio_service.save_audio_file(file_content, audio_file.filename)
        
        # Get the recording to update it directly (since service doesn't handle file operations)
        recording = recording_service.get_recording(recording_id)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Update via repository (simplified approach for file upload)
        from app.repositories.recording_repository import RecordingRepository
        recording_repo = RecordingRepository(db)
        updated_recording = recording_repo.update(recording_id, {
            'file_name': audio_file.filename,
            'file_path': file_path,
            'file_size_bytes': len(file_content),
            'status': 'stopped'
        })
        
        # Start transcription in background
        background_tasks.add_task(audio_service.transcribe_audio, updated_recording, db)
        
        return RecordingResponse.model_validate(updated_recording)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/{recording_id}/transcribe", response_model=RecordingResponse)
async def transcribe_recording(
    recording_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    try:
        updated_recording = recording_service.initiate_transcription(recording_id)
        if not updated_recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Get the actual model for background task
        from app.repositories.recording_repository import RecordingRepository
        recording_repo = RecordingRepository(db)
        recording_model = recording_repo.get_by_id(recording_id)
        
        # Start transcription in background
        background_tasks.add_task(audio_service.transcribe_audio, recording_model, db)
        
        return updated_recording
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{recording_id}", response_model=RecordingResponse)
def get_recording(
    recording_id: UUID,
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    recording = recording_service.get_recording(recording_id)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found"
        )
    
    return recording


@router.get("/session/{session_id}", response_model=List[RecordingResponse])
def get_session_recordings(
    session_id: UUID,
    db: Session = Depends(get_database)
):
    recording_service = RecordingService(db)
    try:
        return recording_service.get_session_recordings(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )