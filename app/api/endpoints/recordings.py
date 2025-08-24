import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.recording_service import RecordingService
from app.schemas.recording import (
    RecordingResponse,
    RecordingStartRequest,
    RecordingStopRequest,
    RecordingStatusEnum
)
from app.services.audio_service import audio_service
from app.core.config import settings

logger = logging.getLogger(__name__)

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
    logger.info(f"Starting upload for recording {recording_id}, filename: {audio_file.filename}")
    
    try:
        recording_service = RecordingService(db)
        
        # Check file size first
        logger.info("Reading file content...")
        file_content = await audio_file.read()
        logger.info(f"File size: {len(file_content)} bytes")
        
        if len(file_content) > settings.MAX_FILE_SIZE:
            logger.error(f"File too large: {len(file_content)} > {settings.MAX_FILE_SIZE}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Validate using service (will check existence and state)
        logger.info("Validating recording upload...")
        try:
            recording_service.upload_audio_file(recording_id, file_content, audio_file.filename)
            logger.info("Recording validation passed")
        except ValueError as e:
            logger.error(f"Recording validation failed: {e}")
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
        
        # Save file with sanitized filename
        logger.info("Saving audio file...")
        file_path = await audio_service.save_audio_file(file_content, audio_file.filename)
        logger.info(f"File saved to: {file_path}")
        
        # Update via repository
        logger.info("Updating recording in database...")
        from app.repositories.recording_repository import RecordingRepository
        recording_repo = RecordingRepository(db)
        
        update_data = {
            'file_name': audio_file.filename,
            'file_path': file_path,
            'file_size_bytes': len(file_content),
            'status': RecordingStatusEnum.UPLOADED
        }
        logger.info(f"Update data: {update_data}")
        
        updated_recording = recording_repo.update(recording_id, update_data)
        logger.info(f"Recording updated: {updated_recording.id if updated_recording else 'None'}")
        
        if not updated_recording:
            logger.error("Failed to update recording - returned None")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update recording in database"
            )
        
        # Start transcription and diarization in background
        logger.info("Starting background processing task...")
        background_tasks.add_task(process_audio_complete, recording_id, db)
        
        logger.info("Creating response...")
        response = RecordingResponse.model_validate(updated_recording)
        logger.info(f"Upload completed successfully for recording {recording_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed with unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


async def process_audio_complete(recording_id: UUID, db: Session):
    """Complete audio processing: transcription + diarization"""
    logger.info(f"Starting background processing for recording {recording_id}")
    
    try:
        from app.repositories.recording_repository import RecordingRepository
        
        recording_repo = RecordingRepository(db)
        recording = recording_repo.get_by_id(recording_id)
        
        if not recording:
            logger.error(f"Recording {recording_id} not found for processing")
            return
        
        logger.info(f"Found recording: {recording.file_path}")
        
        # Step 1: Update status to processing
        logger.info("Updating status to processing...")
        recording_repo.update(recording_id, {'status': RecordingStatusEnum.PROCESSING})
        
        # Step 2: Transcribe
        logger.info("Starting transcription...")
        recording_repo.update(recording_id, {'status': RecordingStatusEnum.TRANSCRIBING})
        transcript = await audio_service.transcribe_audio(recording, db)
        logger.info(f"Transcription result: {'Success' if transcript else 'Failed'}")
        
        if transcript:
            # Step 3: Diarize if enabled
            if settings.ENABLE_SPEAKER_DIARIZATION:
                logger.info("Starting diarization...")
                # Refresh recording to get updated transcript_segments
                db.refresh(recording)
                recording_repo.update(recording_id, {'status': RecordingStatusEnum.DIARIZING})
                diarization_success = await audio_service.perform_speaker_diarization(recording, db)
                logger.info(f"Diarization result: {'Success' if diarization_success else 'Failed'}")
            
            # Final status: completed
            logger.info("Setting status to completed")
            recording_repo.update(recording_id, {'status': RecordingStatusEnum.COMPLETED})
            logger.info(f"Background processing completed successfully for recording {recording_id}")
        else:
            logger.error("Transcription failed, setting status to failed")
            recording_repo.update(recording_id, {'status': RecordingStatusEnum.FAILED})
            
    except Exception as e:
        logger.error(f"Background processing failed for recording {recording_id}: {str(e)}", exc_info=True)
        recording_repo.update(recording_id, {
            'status': RecordingStatusEnum.FAILED,
            'processing_error': str(e)
        })


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