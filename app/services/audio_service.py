import os
import logging
from typing import Optional, List
from pathlib import Path
import aiofiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recording import Recording, RecordingStatusEnum
from app.schemas.recording import TranscriptSegment, SpeakerEnum

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    import assemblyai as aai
    ASSEMBLYAI_AVAILABLE = True
    logger.info("AssemblyAI SDK imported successfully")
except ImportError as e:
    ASSEMBLYAI_AVAILABLE = False
    aai = None
    logger.error(f"Failed to import AssemblyAI SDK: {e}")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    openai = None
    logger.error(f"Failed to import OpenAI: {e}")


class AudioService:
    def __init__(self):
        logger.info("Initializing AudioService")
        
        # Initialize AssemblyAI client
        if ASSEMBLYAI_AVAILABLE and settings.ASSEMBLYAI_API_KEY:
            aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
            logger.info("AssemblyAI client initialized")
            self.use_assemblyai = settings.USE_ASSEMBLYAI
        else:
            logger.warning("AssemblyAI not available or API key not configured")
            self.use_assemblyai = False
        
        # Initialize OpenAI client as fallback
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized as fallback")
        else:
            self.openai_client = None
            logger.warning("OpenAI not available or API key not configured")
        
        logger.info(f"Using AssemblyAI: {self.use_assemblyai}")
        logger.info(f"Speaker diarization enabled: {settings.ENABLE_SPEAKER_DIARIZATION}")
    
    async def save_audio_file(self, file_content: bytes, filename: str) -> str:
        """Save audio file to disk and return file path"""
        import uuid
        import re
        
        # Ensure upload directory exists
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # Sanitize filename - remove special characters and spaces
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Generate unique filename to avoid conflicts
        file_extension = Path(safe_filename).suffix
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        file_path = upload_dir / unique_name
        
        logger.info(f"Saving audio file: {filename} -> {file_path}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        logger.info(f"Audio file saved successfully: {file_path}")
        return str(file_path)
    
    async def transcribe_audio(self, recording: Recording, db: Session) -> Optional[str]:
        """Transcribe audio file using OpenAI Whisper (preferred) or AssemblyAI fallback"""
        logger.info(f"Starting transcription for {recording.file_path}")
        
        # Try OpenAI Whisper first for ambient listening
        try:
            logger.info("Attempting transcription with OpenAI Whisper (ambient listening)")
            return await self._transcribe_with_openai(recording, db)
        except Exception as whisper_error:
            logger.warning(f"OpenAI Whisper failed: {whisper_error}")
            
            # Fallback to AssemblyAI if available
            if self.use_assemblyai and ASSEMBLYAI_AVAILABLE:
                logger.info("Falling back to AssemblyAI")
                try:
                    return await self._transcribe_with_assemblyai(recording, db)
                except Exception as aai_error:
                    logger.error(f"AssemblyAI also failed: {aai_error}")
                    return None
            else:
                logger.error("No transcription service available")
                return None
    
    async def _transcribe_with_assemblyai(self, recording: Recording, db: Session) -> Optional[str]:
        """Transcribe using AssemblyAI with built-in speaker diarization"""
        try:
            logger.info("Starting AssemblyAI transcription...")
            
            # Configure transcription settings
            config = aai.TranscriptionConfig(
                speaker_labels=settings.ENABLE_SPEAKER_DIARIZATION,
                speakers_expected=settings.ASSEMBLYAI_SPEAKERS_EXPECTED if settings.ENABLE_SPEAKER_DIARIZATION else None
            )
            
            # Create transcriber
            transcriber = aai.Transcriber(config=config)
            
            # Transcribe the audio file
            logger.info("Sending file to AssemblyAI...")
            transcript = transcriber.transcribe(recording.file_path)
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"AssemblyAI transcription failed: {transcript.error}")
                recording.status = RecordingStatusEnum.FAILED
                recording.processing_error = f"AssemblyAI error: {transcript.error}"
                db.commit()
                return None
            
            # Extract transcript text
            transcript_text = transcript.text
            logger.info(f"Transcription completed, length: {len(transcript_text)} characters")
            
            # Process segments
            segments = []
            if settings.ENABLE_SPEAKER_DIARIZATION and transcript.utterances:
                logger.info(f"Processing {len(transcript.utterances)} utterances with speaker labels")
                
                for utterance in transcript.utterances:
                    # Map AssemblyAI speaker labels to our enum
                    if utterance.speaker == "A":
                        speaker = SpeakerEnum.PRACTITIONER
                    elif utterance.speaker == "B":
                        speaker = SpeakerEnum.PATIENT
                    else:
                        speaker = SpeakerEnum.UNKNOWN
                    
                    segments.append(TranscriptSegment(
                        text=utterance.text,
                        speaker=speaker,
                        start_time=utterance.start / 1000.0,  # Convert ms to seconds
                        end_time=utterance.end / 1000.0,
                        confidence=utterance.confidence
                    ))
                    logger.info(f"Segment: Speaker {speaker.value} ({utterance.start/1000.0:.2f}s-{utterance.end/1000.0:.2f}s): {utterance.text[:50]}...")
            
            else:
                # No speaker diarization, create segments from words if available
                if transcript.words:
                    logger.info("Creating segments from words (no diarization)")
                    current_segment = {"words": [], "start": None, "end": None}
                    
                    for word in transcript.words:
                        if current_segment["start"] is None:
                            current_segment["start"] = word.start
                        current_segment["words"].append(word.text)
                        current_segment["end"] = word.end
                        
                        # Create segment every ~10 seconds or 50 words
                        if (word.end - current_segment["start"]) > 10000 or len(current_segment["words"]) > 50:
                            segments.append(TranscriptSegment(
                                text=" ".join(current_segment["words"]),
                                speaker=SpeakerEnum.UNKNOWN,
                                start_time=current_segment["start"] / 1000.0,
                                end_time=current_segment["end"] / 1000.0,
                                confidence=0.8  # Default confidence
                            ))
                            current_segment = {"words": [], "start": None, "end": None}
                    
                    # Add final segment if any words remain
                    if current_segment["words"]:
                        segments.append(TranscriptSegment(
                            text=" ".join(current_segment["words"]),
                            speaker=SpeakerEnum.UNKNOWN,
                            start_time=current_segment["start"] / 1000.0,
                            end_time=current_segment["end"] / 1000.0,
                            confidence=0.8
                        ))
            
            # Update recording with results
            recording.transcript = transcript_text
            recording.transcript_segments = [seg.dict() for seg in segments] if segments else None
            recording.status = RecordingStatusEnum.COMPLETED
            recording.processing_error = None
            
            # Mark JSON field as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(recording, "transcript_segments")
            
            db.commit()
            logger.info("AssemblyAI transcription completed successfully")
            
            return transcript_text
            
        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {str(e)}", exc_info=True)
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = str(e)
            db.commit()
            return None
    
    async def _transcribe_with_openai(self, recording: Recording, db: Session) -> Optional[str]:
        """Fallback transcription using OpenAI Whisper"""
        if not self.openai_client:
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = "OpenAI API key not configured"
            db.commit()
            return None
        
        try:
            logger.info("Starting OpenAI Whisper transcription for ambient listening...")
            
            # Transcribe audio with enhanced settings for healthcare consultation
            with open(recording.file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model=settings.WHISPER_MODEL,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    prompt="This is a healthcare consultation between a doctor and patient. Please provide accurate transcription of medical terminology."
                )
            
            # Extract transcript text
            transcript_text = transcript.text
            
            # Extract segments if available
            segments = []
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    segments.append(TranscriptSegment(
                        text=segment.text,
                        speaker=SpeakerEnum.UNKNOWN,
                        start_time=segment.start,
                        end_time=segment.end,
                        confidence=getattr(segment, 'avg_logprob', None)
                    ))
            
            # Update recording with transcript
            recording.transcript = transcript_text
            recording.transcript_segments = [seg.dict() for seg in segments] if segments else None
            recording.status = RecordingStatusEnum.COMPLETED
            recording.processing_error = None
            
            db.commit()
            logger.info("OpenAI transcription completed")
            
            return transcript_text
            
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {str(e)}", exc_info=True)
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = str(e)
            db.commit()
            return None
    
    async def perform_speaker_diarization(self, recording: Recording, db: Session) -> bool:
        """Legacy method - diarization now handled by AssemblyAI"""
        logger.info("Speaker diarization is now handled directly by AssemblyAI during transcription")
        return True
    
    def validate_audio_file(self, filename: str) -> bool:
        """Validate if the file is an allowed audio format"""
        file_extension = filename.lower().split('.')[-1]
        return file_extension in settings.ALLOWED_AUDIO_EXTENSIONS
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)


audio_service = AudioService()