import os
import asyncio
import logging
from typing import Optional, List
from pathlib import Path
import aiofiles
import openai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recording import Recording, RecordingStatusEnum
from app.schemas.recording import TranscriptSegment, SpeakerEnum

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from pyannote.audio import Pipeline
    import torch
    DIARIZATION_AVAILABLE = True
    logger.info("Pyannote.audio imported successfully")
except ImportError as e:
    DIARIZATION_AVAILABLE = False
    Pipeline = None
    logger.error(f"Failed to import pyannote.audio: {e}")


class AudioService:
    def __init__(self):
        logger.info("Initializing AudioService")
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        logger.info(f"OpenAI client initialized: {bool(self.client)}")
        
        self.diarization_pipeline = None
        logger.info(f"Diarization available: {DIARIZATION_AVAILABLE}")
        logger.info(f"Speaker diarization enabled: {settings.ENABLE_SPEAKER_DIARIZATION}")
        logger.info(f"HuggingFace token present: {bool(getattr(settings, 'HUGGING_FACE_TOKEN', None))}")
        
        if DIARIZATION_AVAILABLE and settings.ENABLE_SPEAKER_DIARIZATION:
            try:
                logger.info("Loading diarization pipeline...")
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=getattr(settings, 'HUGGING_FACE_TOKEN', None)
                )
                logger.info("Diarization pipeline loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load diarization pipeline: {e}")
                self.diarization_pipeline = None
    
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
        """Transcribe audio file using OpenAI Whisper"""
        if not self.client:
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = "OpenAI API key not configured"
            db.commit()
            return None
        
        try:
            # Update status to processing
            recording.status = RecordingStatusEnum.PROCESSING
            db.commit()
            
            # Transcribe audio
            with open(recording.file_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=settings.WHISPER_MODEL,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Extract transcript text
            transcript_text = transcript.text
            
            # Extract segments if available
            segments = []
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    segments.append(TranscriptSegment(
                        text=segment.text,
                        speaker=SpeakerEnum.UNKNOWN,  # Default, can be improved with diarization
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
            
            # Perform speaker diarization if enabled and segments available
            if segments and settings.ENABLE_SPEAKER_DIARIZATION:
                logger.info("Starting speaker diarization...")
                diarization_success = await self.perform_speaker_diarization(recording, db)
                logger.info(f"Speaker diarization result: {diarization_success}")
            else:
                logger.info(f"Skipping diarization - segments: {bool(segments)}, enabled: {settings.ENABLE_SPEAKER_DIARIZATION}")
            
            return transcript_text
            
        except Exception as e:
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = str(e)
            db.commit()
            return None
    
    async def perform_speaker_diarization(self, recording: Recording, db: Session) -> bool:
        """Perform speaker diarization using pyannote.audio"""
        logger.info("Starting perform_speaker_diarization")
        logger.info(f"Diarization enabled: {settings.ENABLE_SPEAKER_DIARIZATION}")
        logger.info(f"Pipeline available: {bool(self.diarization_pipeline)}")
        logger.info(f"Audio file path: {recording.file_path}")
        
        if not settings.ENABLE_SPEAKER_DIARIZATION or not self.diarization_pipeline:
            logger.warning("Diarization skipped - not enabled or pipeline not available")
            return False
        
        try:
            logger.info("Applying diarization to audio file...")
            logger.info(f"File path: {recording.file_path}")
            logger.info(f"File exists: {os.path.exists(recording.file_path)}")
            
            if os.path.exists(recording.file_path):
                logger.info(f"File size: {os.path.getsize(recording.file_path)} bytes")
                
            # Check file format
            file_extension = Path(recording.file_path).suffix.lower()
            logger.info(f"File extension: {file_extension}")
            
            # Apply diarization to the audio file
            diarization = self.diarization_pipeline(recording.file_path)
            logger.info("Diarization completed successfully")
            
            # Log diarization results
            speakers_found = set()
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers_found.add(speaker)
                logger.info(f"Speaker {speaker}: {turn.start:.2f}s - {turn.end:.2f}s")
            
            logger.info(f"Total speakers found: {len(speakers_found)}")
            logger.info(f"Transcript segments available: {bool(recording.transcript_segments)}")
            
            if recording.transcript_segments:
                logger.info(f"Processing {len(recording.transcript_segments)} transcript segments")
                
                # Map speakers to segments based on timestamps
                speaker_map = {}
                speaker_count = 0
                segments_updated = 0
                
                for i, segment_data in enumerate(recording.transcript_segments):
                    start_time = segment_data.get('start_time', 0)
                    end_time = segment_data.get('end_time', 0)
                    
                    logger.info(f"Segment {i}: {start_time:.2f}s - {end_time:.2f}s: '{segment_data.get('text', '')[:50]}...'")
                    
                    # Find the dominant speaker for this segment
                    segment_speakers = {}
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        # Check for overlap with more flexible conditions
                        overlap_start = max(turn.start, start_time)
                        overlap_end = min(turn.end, end_time)
                        overlap = overlap_end - overlap_start
                        
                        if overlap > 0:
                            segment_speakers[speaker] = segment_speakers.get(speaker, 0) + overlap
                            logger.info(f"  Speaker {speaker} overlap: {overlap:.2f}s")
                    
                    if segment_speakers:
                        # Get speaker with most overlap
                        dominant_speaker = max(segment_speakers, key=segment_speakers.get)
                        logger.info(f"  Dominant speaker: {dominant_speaker}")
                        
                        # Map speaker labels to enum values
                        if dominant_speaker not in speaker_map:
                            if speaker_count == 0:
                                speaker_map[dominant_speaker] = SpeakerEnum.PRACTITIONER
                            elif speaker_count == 1:
                                speaker_map[dominant_speaker] = SpeakerEnum.PATIENT
                            else:
                                speaker_map[dominant_speaker] = SpeakerEnum.UNKNOWN
                            speaker_count += 1
                            logger.info(f"  Mapped {dominant_speaker} to {speaker_map[dominant_speaker].value}")
                        
                        old_speaker = segment_data.get('speaker', 'unknown')
                        segment_data['speaker'] = speaker_map[dominant_speaker].value
                        logger.info(f"  Updated speaker: {old_speaker} -> {segment_data['speaker']}")
                        segments_updated += 1
                    else:
                        logger.warning(f"  No speaker overlap found for segment {i}")
                        segment_data['speaker'] = SpeakerEnum.UNKNOWN.value
                
                logger.info(f"Updated {segments_updated} out of {len(recording.transcript_segments)} segments")
                
                # Mark the JSON field as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(recording, "transcript_segments")
                
                db.commit()
                logger.info("Database committed successfully")
                
                # Verify the update by checking the database
                db.refresh(recording)
                logger.info(f"Verification - First segment speaker after commit: {recording.transcript_segments[0].get('speaker', 'NOT_FOUND') if recording.transcript_segments else 'NO_SEGMENTS'}")
                return True
            else:
                logger.warning("No transcript segments to process")
                return False
            
        except Exception as e:
            logger.error(f"Speaker diarization failed: {str(e)}", exc_info=True)
            return False
    
    def validate_audio_file(self, filename: str) -> bool:
        """Validate if the file is an allowed audio format"""
        file_extension = filename.lower().split('.')[-1]
        return file_extension in settings.ALLOWED_AUDIO_EXTENSIONS
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)


audio_service = AudioService()