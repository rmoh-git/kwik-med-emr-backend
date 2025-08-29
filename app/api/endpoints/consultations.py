"""
Healthcare Consultation API Endpoints
Manages LiveKit-based healthcare consultations
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.consultation_service import consultation_service
from app.db.database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response Models
class CreateConsultationRequest(BaseModel):
    session_id: str
    patient_id: str
    practitioner_id: str
    max_duration_minutes: int = 120

class ConsultationResponse(BaseModel):
    room_name: str
    room_sid: str
    session_id: str
    ws_url: str
    created_at: str
    max_duration_minutes: int
    participants: dict
    features: dict
    status: str

class TokenRequest(BaseModel):
    room_name: str
    participant_identity: str
    participant_type: str = "participant"  # practitioner, patient, observer
    token_ttl_hours: int = 4

class TokenResponse(BaseModel):
    token: str
    participant_identity: str
    participant_type: str
    expires_in_hours: int
    room_name: str

class ActiveRoomResponse(BaseModel):
    room_name: str
    room_sid: str
    num_participants: int
    created_at: str = None
    session_id: str = None
    patient_id: str = None
    practitioner_id: str = None

class ValidationRequest(BaseModel):
    session_id: str
    patient_id: str
    practitioner_id: str

class ValidationResponse(BaseModel):
    valid: bool
    session_exists: bool
    patient_exists: bool
    practitioner_exists: bool
    session_matches_patient: bool
    errors: List[str]

# Simplified consultation models - no live transcription

@router.post("/create", response_model=ConsultationResponse)
async def create_consultation(
    request: CreateConsultationRequest,
    db: Session = Depends(get_db)
):
    """Create a new healthcare consultation room"""
    
    try:
        logger.info(f"Creating consultation for session: {request.session_id}")
        logger.info(f"Validating session, patient, and practitioner...")
        
        consultation_info = await consultation_service.create_consultation_room(
            session_id=request.session_id,
            patient_id=request.patient_id,
            practitioner_id=request.practitioner_id,
            max_duration_minutes=request.max_duration_minutes,
            db=db
        )
        
        logger.info(f"Consultation created successfully: {consultation_info['room_name']}")
        return ConsultationResponse(**consultation_info)
        
    except ValueError as e:
        # Validation errors - return 400 Bad Request
        logger.warning(f"Consultation validation failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        # Other errors - return 500 Internal Server Error
        logger.error(f"Failed to create consultation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create consultation: {str(e)}"
        )

@router.post("/token", response_model=TokenResponse)
async def generate_consultation_token(request: TokenRequest):
    """Generate access token for consultation participant"""
    
    try:
        logger.info(f"Generating token for {request.participant_type}: {request.participant_identity}")
        
        token = consultation_service.generate_participant_token(
            room_name=request.room_name,
            participant_identity=request.participant_identity,
            participant_type=request.participant_type,
            token_ttl_hours=request.token_ttl_hours
        )
        
        return TokenResponse(
            token=token,
            participant_identity=request.participant_identity,
            participant_type=request.participant_type,
            expires_in_hours=request.token_ttl_hours,
            room_name=request.room_name
        )
        
    except Exception as e:
        logger.error(f"Failed to generate token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate token: {str(e)}"
        )

@router.post("/{room_name}/end")
async def end_consultation(room_name: str):
    """End a healthcare consultation"""
    
    try:
        logger.info(f"Ending consultation: {room_name}")
        
        result = await consultation_service.end_consultation(room_name)
        
        return {
            "message": "Consultation ended successfully",
            "room_name": room_name,
            "ended_at": result["ended_at"],
            "status": result["status"]
        }
        
    except Exception as e:
        logger.error(f"Failed to end consultation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end consultation: {str(e)}"
        )

@router.get("/active", response_model=List[ActiveRoomResponse])
async def list_active_consultations():
    """List all active healthcare consultation rooms"""
    
    try:
        active_rooms = await consultation_service.list_active_rooms()
        
        return [
            ActiveRoomResponse(
                room_name=room["room_name"],
                room_sid=room["room_sid"],
                num_participants=room["num_participants"],
                created_at=room.get("created_at"),
                session_id=room.get("session_id"),
                patient_id=room.get("patient_id"),
                practitioner_id=room.get("practitioner_id")
            )
            for room in active_rooms
        ]
        
    except Exception as e:
        logger.error(f"Failed to list active consultations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list active consultations: {str(e)}"
        )

@router.post("/validate", response_model=ValidationResponse)
async def validate_consultation_entities(
    request: ValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate that session, patient, and practitioner exist before creating consultation"""
    
    try:
        logger.info(f"Validating entities for session: {request.session_id}")
        
        validation = await consultation_service.validate_consultation_entities(
            session_id=request.session_id,
            patient_id=request.patient_id,
            practitioner_id=request.practitioner_id,
            db=db
        )
        
        is_valid = all([
            validation["session_exists"],
            validation["patient_exists"], 
            validation["practitioner_exists"],
            validation["session_matches_patient"]
        ])
        
        return ValidationResponse(
            valid=is_valid,
            session_exists=validation["session_exists"],
            patient_exists=validation["patient_exists"],
            practitioner_exists=validation["practitioner_exists"],
            session_matches_patient=validation["session_matches_patient"],
            errors=validation["errors"]
        )
        
    except Exception as e:
        logger.error(f"Failed to validate entities: {str(e)}")
        return ValidationResponse(
            valid=False,
            session_exists=False,
            patient_exists=False,
            practitioner_exists=False,
            session_matches_patient=False,
            errors=[f"Validation error: {str(e)}"]
        )

# Live transcription removed - using simple recording + Whisper approach

@router.get("/health")
async def consultation_health_check():
    """Health check for consultation service"""
    
    return {
        "service": "Healthcare Consultations",
        "status": "healthy",
        "livekit_available": consultation_service.livekit_available,
        "features": {
            "room_creation": True,
            "token_generation": True,
            "healthcare_ai_assistant": True,
            "hipaa_compliant": True,
            "entity_validation": True,
            "ambient_recording": True,
            "whisper_transcription": True,
            "post_consultation_analysis": True
        }
    }