"""
Real-time Whisper Healthcare Agent
LiveKit agent that uses OpenAI Whisper for real-time speech recognition
and provides live AI suggestions based on patient history
"""

import asyncio
import logging
import json
import io
import wave
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
import tempfile
import os

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("realtime-whisper-agent")

# Import requirements
try:
    from livekit import rtc, api
    from livekit.agents import (
        AutoSubscribe,
        JobContext,
        JobProcess, 
        WorkerOptions,
        cli
    )
    LIVEKIT_AVAILABLE = True
except ImportError as e:
    LIVEKIT_AVAILABLE = False
    logger.error(f"LiveKit not available: {e}")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.error("OpenAI not available")

# Project imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.db.database import get_db
from app.models.patient import Patient
from app.models.session import Session as SessionModel

class RealTimeWhisperAgent:
    """Real-time Whisper agent for healthcare consultations"""
    
    def __init__(self):
        self.openai_client = None
        self.audio_buffer = {}  # Per participant audio buffer
        self.transcription_buffer = []
        self.patient_context = {}
        self.last_suggestions = set()
        
        # Initialize OpenAI
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI Whisper client ready for real-time transcription")
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for Whisper
        self.buffer_duration = 3.0  # 3 seconds buffer
        self.min_audio_length = 1.0  # Minimum 1 second for transcription
        
    async def load_patient_context(self, session_id: str) -> Dict:
        """Load patient context for AI suggestions"""
        
        try:
            db = next(get_db())
            
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                logger.warning(f"Session {session_id} not found")
                return {}
            
            patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
            if not patient:
                logger.warning(f"Patient not found for session {session_id}")
                return {}
            
            # Build patient context
            context = {
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "age": self._calculate_age(patient.date_of_birth),
                "gender": patient.gender.value,
                "insurance": patient.insurance_provider,
                "national_id": patient.national_id,
                "visit_type": session.visit_type,
                "practitioner": session.practitioner_name,
                "medical_history": []
            }
            
            # Get previous analyses for medical history
            previous_sessions = db.query(SessionModel).filter(
                SessionModel.patient_id == patient.id,
                SessionModel.id != session_id
            ).limit(3).all()
            
            for prev_session in previous_sessions:
                for analysis in prev_session.analyses:
                    if analysis.result and "diagnoses" in analysis.result:
                        for diagnosis in analysis.result["diagnoses"]:
                            context["medical_history"].append({
                                "condition": diagnosis.get("condition", ""),
                                "confidence": diagnosis.get("confidence_score", 0),
                                "date": prev_session.created_at.strftime("%Y-%m-%d")
                            })
            
            self.patient_context = context
            logger.info(f"Patient context loaded: {context['patient_name']}, {len(context['medical_history'])} previous conditions")
            return context
            
        except Exception as e:
            logger.error(f"Error loading patient context: {e}")
            return {}
        finally:
            db.close()
    
    def _calculate_age(self, birth_date) -> int:
        """Calculate age from birth date"""
        today = datetime.now().date()
        if hasattr(birth_date, 'date'):
            birth_date = birth_date.date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    def audio_frame_to_bytes(self, frame: rtc.AudioFrame) -> bytes:
        """Convert AudioFrame to bytes for Whisper"""
        try:
            # Convert audio frame to numpy array
            audio_data = np.frombuffer(frame.data, dtype=np.int16)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if frame.sample_rate != self.sample_rate:
                # Simple resampling (for production, use proper resampling)
                ratio = self.sample_rate / frame.sample_rate
                audio_data = np.interp(
                    np.arange(0, len(audio_data), 1/ratio),
                    np.arange(0, len(audio_data)),
                    audio_data
                ).astype(np.int16)
            
            return audio_data.tobytes()
        except Exception as e:
            logger.error(f"Error converting audio frame: {e}")
            return b""
    
    async def buffer_audio(self, participant_id: str, audio_frame: rtc.AudioFrame):
        """Buffer audio for real-time transcription"""
        
        if participant_id not in self.audio_buffer:
            self.audio_buffer[participant_id] = []
        
        # Convert frame to bytes
        audio_bytes = self.audio_frame_to_bytes(audio_frame)
        if audio_bytes:
            self.audio_buffer[participant_id].append(audio_bytes)
            
            # Calculate buffer duration
            bytes_per_second = self.sample_rate * 2  # 16-bit = 2 bytes per sample
            current_duration = len(b''.join(self.audio_buffer[participant_id])) / bytes_per_second
            
            # Transcribe when buffer is full or has enough audio
            if current_duration >= self.buffer_duration:
                suggestion = await self.transcribe_buffer(participant_id)
                return suggestion
    
    async def transcribe_buffer(self, participant_id: str):
        """Transcribe buffered audio with Whisper"""
        
        if not self.openai_client or participant_id not in self.audio_buffer:
            return
        
        try:
            # Get audio buffer
            audio_data = b''.join(self.audio_buffer[participant_id])
            if len(audio_data) < self.sample_rate * 2 * self.min_audio_length:  # Too short
                return
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                # Write WAV header and data
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_data)
                
                # Transcribe with Whisper
                with open(temp_file.name, 'rb') as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        language="en",
                        prompt="Healthcare consultation between doctor and patient. Medical terminology."
                    )
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                # Process transcription
                if transcript and transcript.strip():
                    suggestion = await self.process_transcription(participant_id, transcript.strip())
                    return suggestion
                
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
        finally:
            # Clear buffer (keep small overlap)
            if participant_id in self.audio_buffer:
                overlap_samples = int(self.sample_rate * 0.5 * 2)  # 0.5 second overlap
                if len(self.audio_buffer[participant_id]) > 1:
                    last_chunk = self.audio_buffer[participant_id][-1]
                    if len(last_chunk) > overlap_samples:
                        self.audio_buffer[participant_id] = [last_chunk[-overlap_samples:]]
                    else:
                        self.audio_buffer[participant_id] = []
                else:
                    self.audio_buffer[participant_id] = []
    
    async def process_transcription(self, participant_id: str, text: str):
        """Process transcription and generate AI suggestions"""
        
        # Add to transcription buffer
        timestamp = datetime.now()
        speaker_type = "practitioner" if "dr" in participant_id.lower() or "doctor" in participant_id.lower() else "patient"
        
        transcription_entry = {
            "timestamp": timestamp.isoformat(),
            "participant_id": participant_id,
            "speaker_type": speaker_type,
            "text": text
        }
        
        self.transcription_buffer.append(transcription_entry)
        
        # Enhanced logging for real-time monitoring
        logger.info("=" * 80)
        logger.info(f"🎤 LIVE TRANSCRIPTION | {speaker_type.upper()} ({participant_id})")
        logger.info(f"📝 SPEECH: \"{text}\"")
        logger.info(f"⏰ TIME: {timestamp.strftime('%H:%M:%S')}")
        logger.info("=" * 80)
        
        # Keep only last 10 entries
        if len(self.transcription_buffer) > 10:
            self.transcription_buffer = self.transcription_buffer[-10:]
        
        # Generate AI suggestion
        suggestion = await self.generate_ai_suggestion(text, speaker_type)
        
        if suggestion:
            logger.info("🧠 AI ANALYSIS RESULT:")
            logger.info(f"   💡 SUGGESTION: {suggestion['content']}")
            logger.info(f"   🚨 PRIORITY: {suggestion['priority'].upper()}")
            logger.info(f"   📂 CATEGORY: {suggestion['category'].upper()}")
            logger.info(f"   🎯 TRIGGERED BY: \"{suggestion['triggered_by']}\"")
            logger.info("-" * 80)
            return suggestion
        else:
            logger.info("🤔 AI ANALYSIS: No suggestion generated for this input")
            logger.info("-" * 80)
        
        return None
    
    async def generate_ai_suggestion(self, current_text: str, speaker_type: str) -> Optional[Dict]:
        """Generate contextual AI suggestion"""
        
        if not self.openai_client or not self.patient_context:
            return None
        
        # Build conversation context
        recent_conversation = "\n".join([
            f"{entry['speaker_type']}: {entry['text']}" 
            for entry in self.transcription_buffer[-5:]
        ])
        
        # Build patient context
        patient_info = f"""
Patient: {self.patient_context.get('patient_name', 'Unknown')} 
Age: {self.patient_context.get('age', 'N/A')}
Gender: {self.patient_context.get('gender', 'N/A')}
Visit Type: {self.patient_context.get('visit_type', 'General')}
Previous Conditions: {'; '.join([h['condition'] for h in self.patient_context.get('medical_history', [])[:3]])}
"""
        
        # Check if we should provide suggestion
        suggestion_trigger_keywords = [
            'pain', 'hurt', 'symptom', 'feel', 'chest', 'head', 'dizzy', 'nausea',
            'fever', 'cough', 'breath', 'medication', 'treatment', 'diagnosis'
        ]
        
        if not any(keyword in current_text.lower() for keyword in suggestion_trigger_keywords):
            return None
        
        # TODO: RAG Integration Point - Replace this prompt with RAG-enhanced context
        # Future: Add medical knowledge base, clinical guidelines, drug interactions, etc.
        prompt = f"""
You are an AI healthcare assistant providing real-time suggestions during a consultation.

PATIENT CONTEXT:
{patient_info}

RECENT CONVERSATION:
{recent_conversation}

CURRENT: {speaker_type} just said: "{current_text}"

Provide a brief suggestion for the practitioner if relevant. Focus on:
- Diagnostic questions to ask
- Symptoms to investigate further  
- Red flags or urgent concerns
- Treatment considerations based on patient history

Keep under 80 words. Only suggest if valuable. 
Respond with JSON: {{"content": "suggestion", "priority": "low|medium|high", "category": "diagnosis|treatment|questions|alert"}}

If no suggestion needed, respond: {{"content": null}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster for real-time
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.2
            )
            
            suggestion_text = response.choices[0].message.content.strip()
            suggestion_json = json.loads(suggestion_text)
            
            if suggestion_json.get("content") is None:
                return None
            
            # Add metadata
            suggestion_json.update({
                "timestamp": datetime.now().isoformat(),
                "triggered_by": current_text,
                "speaker": speaker_type
            })
            
            return suggestion_json
            
        except Exception as e:
            logger.error(f"AI suggestion error: {e}")
            return None

# Global agent instance
whisper_agent = RealTimeWhisperAgent()

def prewarm(proc: JobProcess):
    """Prewarm process"""
    logger.info("Prewarming real-time Whisper agent")

def extract_session_id(room_name: str) -> str:
    """Extract session ID from room name"""
    if room_name.startswith("consultation_"):
        return room_name.replace("consultation_", "")
    return room_name

async def entrypoint(ctx: JobContext):
    """Main entrypoint for real-time Whisper agent"""
    
    if not LIVEKIT_AVAILABLE or not OPENAI_AVAILABLE:
        logger.error("Required dependencies not available")
        return
    
    logger.info(f"🏥 Starting Real-time Whisper Healthcare Agent")
    logger.info(f"🎤 Room: {ctx.room.name}")
    
    # Extract session and load patient context
    session_id = extract_session_id(ctx.room.name)
    await whisper_agent.load_patient_context(session_id)
    
    # Connect to room for audio only
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("🔗 Connected to room for ambient listening")
    
    # Log room status
    logger.info("=" * 80)
    logger.info(f"🏠 ROOM STATUS AFTER CONNECTION:")
    logger.info(f"   Room Name: {ctx.room.name}")
    logger.info(f"   Room SID: {ctx.room.sid}")
    logger.info(f"   Local Participant: {ctx.room.local_participant.identity}")
    logger.info(f"   Remote Participants: {len(ctx.room.remote_participants)}")
    for participant in ctx.room.remote_participants.values():
        logger.info(f"      - {participant.identity} ({participant.sid})")
    logger.info("=" * 80)
    
    # Track audio subscriptions
    audio_tasks = {}
    
    @ctx.room.on("track_subscribed") 
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.Participant):
        logger.info(f"📡 TRACK SUBSCRIBED from {participant.identity}")
        logger.info(f"   Track Kind: {track.kind}")
        logger.info(f"   Track SID: {track.sid}")
        logger.info(f"   Publication: {publication.name if publication else 'Unknown'}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎵 Starting audio processing for {participant.identity}")
            
            # Start audio processing task for this participant
            audio_tasks[participant.identity] = asyncio.create_task(
                process_audio_track(track, participant)
            )
        else:
            logger.info(f"ℹ️ Non-audio track ignored: {track.kind}")
    
    @ctx.room.on("track_unsubscribed")
    def on_track_unsubscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.Participant):
        if participant.identity in audio_tasks:
            audio_tasks[participant.identity].cancel()
            del audio_tasks[participant.identity]
            logger.info(f"🔇 Stopped processing audio from {participant.identity}")
    
    async def process_audio_track(track: rtc.AudioTrack, participant: rtc.Participant):
        """Process audio track for real-time transcription"""
        
        logger.info("=" * 80)
        logger.info(f"🎵 STARTED AUDIO PROCESSING for {participant.identity}")
        logger.info(f"   Track: {track}")
        logger.info(f"   Sample Rate: {getattr(track, 'sample_rate', 'Unknown')}")
        logger.info("=" * 80)
        
        audio_stream = rtc.AudioStream(track)
        frame_count = 0
        
        async for frame in audio_stream:
            frame_count += 1
            try:
                # Log every 50th frame to avoid spam
                if frame_count % 50 == 1:
                    logger.info(f"🎤 AUDIO FRAME #{frame_count} from {participant.identity}")
                    logger.info(f"   Frame size: {len(frame.data) if hasattr(frame, 'data') else 'Unknown'} bytes")
                    logger.info(f"   Sample rate: {getattr(frame, 'sample_rate', 'Unknown')} Hz")
                    logger.info(f"   Channels: {getattr(frame, 'channels', 'Unknown')}")
                
                # Buffer audio for transcription and get potential suggestion
                suggestion = await whisper_agent.buffer_audio(participant.identity, frame)
                
                # If we got a suggestion, broadcast it to the room
                if suggestion:
                    logger.info("🔔 AI SUGGESTION GENERATED - Broadcasting to frontend...")
                    
                    # Send transcription data to frontend
                    transcription_data = {
                        "type": "transcription",
                        "data": {
                            "participant_id": participant.identity,
                            "speaker_type": "practitioner" if "dr" in participant.identity.lower() else "patient",
                            "text": suggestion.get("triggered_by", ""),
                            "timestamp": suggestion.get("timestamp")
                        }
                    }
                    
                    # Send AI suggestion to frontend
                    suggestion_data = {
                        "type": "ai_suggestion", 
                        "data": suggestion
                    }
                    
                    # Broadcast via data channel
                    await ctx.room.local_participant.publish_data(
                        json.dumps(transcription_data).encode(), reliable=True
                    )
                    
                    await ctx.room.local_participant.publish_data(
                        json.dumps(suggestion_data).encode(), reliable=True
                    )
                    
                    logger.info(f"📡 Successfully broadcasted to {len(ctx.room.remote_participants)} participants")
                
            except Exception as e:
                logger.error(f"❌ Audio processing error for {participant.identity}: {e}")
                logger.error(f"   Frame #{frame_count}")
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
    
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.Participant):
        logger.info("=" * 60)
        logger.info(f"👤 PARTICIPANT CONNECTED: {participant.identity}")
        logger.info(f"   Participant SID: {participant.sid}")
        logger.info(f"   Participant Name: {getattr(participant, 'name', 'Unknown')}")
        logger.info("=" * 60)
    
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.Participant):
        logger.info("=" * 60)
        logger.info(f"👋 PARTICIPANT DISCONNECTED: {participant.identity}")
        logger.info("=" * 60)
    
    @ctx.room.on("data_received")
    def on_data_received(data: bytes, participant: rtc.Participant):
        logger.info("=" * 60)
        logger.info(f"📨 DATA RECEIVED from {participant.identity}")
        try:
            message = json.loads(data.decode())
            logger.info(f"   📄 Message Type: {message.get('type', 'unknown')}")
            logger.info(f"   📦 Message Data: {message}")
        except Exception as e:
            logger.info(f"   ❌ Could not parse data: {e}")
            logger.info(f"   📄 Raw data: {data}")
        logger.info("=" * 60)
    
    # Send periodic status updates
    async def send_status_updates():
        while True:
            try:
                await ctx.room.local_participant.publish_data(
                    json.dumps({
                        "type": "agent_status",
                        "status": "listening",
                        "timestamp": datetime.now().isoformat(),
                        "transcription_count": len(whisper_agent.transcription_buffer)
                    }).encode(),
                    reliable=False
                )
                await asyncio.sleep(10)  # Status every 10 seconds
            except Exception as e:
                logger.error(f"Status update error: {e}")
                break
    
    # Start status updates
    status_task = asyncio.create_task(send_status_updates())
    
    try:
        logger.info("🤖 Agent ready for real-time ambient listening with AI suggestions")
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Agent shutting down...")
    finally:
        # Cleanup
        status_task.cancel()
        for task in audio_tasks.values():
            task.cancel()

if __name__ == "__main__":
    if not LIVEKIT_AVAILABLE:
        print("❌ LiveKit agents not available")
        exit(1)
    
    if not OPENAI_AVAILABLE:
        print("❌ OpenAI not available")  
        exit(1)
    
    print("🏥 Starting Real-time Whisper Healthcare Agent")
    print("🎤 Ready for ambient listening with live AI suggestions")
    
    options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        ws_url=settings.LIVEKIT_URL
    )
    
    cli.run_app(options)