"""
Healthcare Consultation Service
Manages LiveKit rooms for healthcare consultations
"""

import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
import uuid

try:
    from livekit import api
    from livekit.api import AccessToken, VideoGrants
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False

from app.core.config import settings
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.session import Session as SessionModel
from app.models.patient import Patient
from app.models.practitioner import Practitioner

logger = logging.getLogger(__name__)

class HealthcareConsultationService:
    """Service for managing healthcare consultation rooms"""
    
    def __init__(self):
        """Initialize the consultation service"""
        self.livekit_available = LIVEKIT_AVAILABLE
        self._lk_api = None
        
        if not self.livekit_available:
            logger.warning("LiveKit not available - consultation service running in mock mode")
            
        logger.info("Healthcare Consultation Service initialized")
    
    @property
    def lk_api(self):
        """Lazy initialization of LiveKit API client"""
        if not self.livekit_available:
            return None
            
        if self._lk_api is None and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET:
            self._lk_api = api.LiveKitAPI(
                url=settings.LIVEKIT_URL,
                api_key=settings.LIVEKIT_API_KEY,
                api_secret=settings.LIVEKIT_API_SECRET
            )
        return self._lk_api
    
    async def validate_consultation_entities(
        self,
        session_id: str,
        patient_id: str,
        practitioner_id: str,
        db: Session
    ) -> Dict[str, bool]:
        """Validate that session, patient, and practitioner exist"""
        
        validation_results = {
            "session_exists": False,
            "patient_exists": False,
            "practitioner_exists": False,
            "session_matches_patient": False,
            "errors": []
        }
        
        try:
            # Check if session exists
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            logger.info(type(session.patient_id))
            logger.info(patient_id.lstrip()==str(session.patient_id).lstrip())
            if session:
                validation_results["session_exists"] = True
                
                # Check if session belongs to the specified patient
                if str(session.patient_id) == patient_id:
                    logger.info(session.patient_id)
                    logger.info(patient_id)
                    validation_results["session_matches_patient"] = True
                else:
                    validation_results["errors"].append(f"Session {session_id} does not belong to patient {patient_id}")
            else:
                validation_results["errors"].append(f"Session {session_id} not found")
            
            # Check if patient exists
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if patient:
                validation_results["patient_exists"] = True
            else:
                validation_results["errors"].append(f"Patient {patient_id} not found")
            
            # Check if practitioner exists
            practitioner = db.query(Practitioner).filter(Practitioner.id == practitioner_id).first()
            if practitioner:
                validation_results["practitioner_exists"] = True
            else:
                validation_results["errors"].append(f"Practitioner {practitioner_id} not found")
                
        except Exception as e:
            validation_results["errors"].append(f"Database validation error: {str(e)}")
            logger.error(f"Validation error: {str(e)}")
        
        return validation_results

    async def create_consultation_room(
        self, 
        session_id: str,
        patient_id: str,
        practitioner_id: str,
        max_duration_minutes: int = 120,
        db: Session = None
    ) -> Dict:
        """Create a consultation room for healthcare sessions"""
        
        # Validate entities exist if database session provided
        if db:
            validation = await self.validate_consultation_entities(
                session_id, patient_id, practitioner_id, db
            )
            
            if not all([
                validation["session_exists"],
                validation["patient_exists"], 
                validation["practitioner_exists"],
                validation["session_matches_patient"]
            ]):
                raise ValueError(
                    f"Validation failed: {', '.join(validation['errors'])}"
                )
        
        room_name = f"consultation_{session_id}"
        
        try:
            if not self.livekit_available or not self.lk_api:
                # Mock mode
                logger.info(f"Creating consultation room in mock mode: {room_name}")
                room_sid = f"mock_room_{uuid.uuid4().hex[:12]}"
            else:
                # Try real LiveKit room creation, fallback to mock on failure
                try:
                    room_config = api.CreateRoomRequest(
                        name=room_name,
                        empty_timeout=max_duration_minutes * 60,  # Convert to seconds
                        max_participants=5,  # Practitioner, patient, + observers
                        metadata=json.dumps({
                            "session_id": session_id,
                            "patient_id": patient_id,
                            "practitioner_id": practitioner_id,
                            "consultation_type": "healthcare",
                            "created_at": datetime.now().isoformat(),
                            "max_duration_minutes": max_duration_minutes
                        })
                    )
                    
                    room = await self.lk_api.room.create_room(room_config)
                    room_sid = room.sid
                    logger.info(f"Created real LiveKit room: {room_name} (SID: {room_sid})")
                except Exception as lk_error:
                    logger.warning(f"LiveKit server not available, falling back to mock mode: {str(lk_error)}")
                    room_sid = f"mock_room_{uuid.uuid4().hex[:12]}"
            
            logger.info(f"Created consultation room: {room_name} (SID: {room_sid})")
            
            return {
                "room_name": room_name,
                "room_sid": room_sid,
                "session_id": session_id,
                "ws_url": settings.LIVEKIT_URL or "ws://localhost:7880",
                "created_at": datetime.now().isoformat(),
                "max_duration_minutes": max_duration_minutes,
                "participants": {
                    "max_participants": 5,
                    "current_participants": 0
                },
                "features": {
                    "healthcare_ai_assistant": True,
                    "real_time_transcription": True,
                    "secure_recording": True,
                    "hipaa_compliant": True
                },
                "status": "ready" if room_sid.startswith("RM_") else "mock_ready"
            }
            
        except Exception as e:
            logger.error(f"Failed to create consultation room: {str(e)}")
            raise
    
    def generate_participant_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_type: str = "participant",
        token_ttl_hours: int = 4
    ) -> str:
        """Generate access token for room participant"""
        
        if not self.livekit_available:
            # Return mock token for testing
            return f"mock_token_{participant_identity}_{uuid.uuid4().hex[:8]}"
        
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise ValueError("LiveKit credentials not configured")
        
        try:
            # Set permissions based on participant type
            if participant_type == "practitioner":
                grants = VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                    recorder=True  # Practitioners can control recording
                )
            elif participant_type == "patient":
                grants = VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=False,
                    recorder=False
                )
            else:  # observer, specialist, etc.
                grants = VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=False,
                    can_subscribe=True,
                    can_publish_data=False,
                    recorder=False
                )
            
            # Create token with healthcare metadata
            token = AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            token.with_identity(participant_identity)
            token.with_grants(grants)
            token.with_metadata(json.dumps({
                "participant_type": participant_type,
                "healthcare_role": participant_type,
                "joined_at": datetime.now().isoformat(),
                "permissions": {
                    "can_record": participant_type == "practitioner",
                    "can_control_ai": participant_type == "practitioner"
                }
            }))
            
            # Token valid for specified hours
            token.with_ttl(timedelta(hours=token_ttl_hours))
            
            logger.info(f"Generated token for {participant_type}: {participant_identity}")
            return token.to_jwt()
            
        except Exception as e:
            logger.error(f"Failed to generate participant token: {str(e)}")
            raise
    
    async def end_consultation(self, room_name: str) -> Dict:
        """End a consultation and cleanup resources"""
        
        try:
            if self.livekit_available and self.lk_api:
                try:
                    await self.lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
                    logger.info(f"Deleted LiveKit room: {room_name}")
                except Exception as lk_error:
                    logger.warning(f"Could not delete LiveKit room, continuing with mock cleanup: {str(lk_error)}")
            else:
                logger.info(f"Mock mode: Ended consultation room: {room_name}")
            
            return {
                "room_name": room_name,
                "ended_at": datetime.now().isoformat(),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error ending consultation: {str(e)}")
            # Don't raise in mock mode, just log and return success
            logger.info(f"Continuing with mock cleanup for room: {room_name}")
            return {
                "room_name": room_name,
                "ended_at": datetime.now().isoformat(),
                "status": "completed"
            }
    
    async def list_active_rooms(self) -> list:
        """List active consultation rooms"""
        
        try:
            if not self.livekit_available or not self.lk_api:
                logger.info("Mock mode: Returning empty room list")
                return []  # Mock mode returns empty list
            
            try:
                rooms = await self.lk_api.room.list_rooms(api.ListRoomsRequest())
                
                healthcare_rooms = []
                for room in rooms.rooms:
                    # Filter for healthcare consultation rooms
                    if room.name.startswith("consultation_"):
                        try:
                            metadata = json.loads(room.metadata) if room.metadata else {}
                            healthcare_rooms.append({
                                "room_name": room.name,
                                "room_sid": room.sid,
                                "num_participants": room.num_participants,
                                "created_at": metadata.get("created_at"),
                                "session_id": metadata.get("session_id"),
                                "patient_id": metadata.get("patient_id"),
                                "practitioner_id": metadata.get("practitioner_id")
                            })
                        except Exception:
                            # Skip rooms with invalid metadata
                            continue
                
                return healthcare_rooms
            
            except Exception as lk_error:
                logger.warning(f"LiveKit not available, returning empty list: {str(lk_error)}")
                return []
            
        except Exception as e:
            logger.error(f"Error listing active rooms: {str(e)}")
            return []

# Global service instance
consultation_service = HealthcareConsultationService()