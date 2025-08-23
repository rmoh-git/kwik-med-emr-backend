import os
import asyncio
from typing import Optional, List
from pathlib import Path
import aiofiles
import openai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recording import Recording, RecordingStatusEnum
from app.schemas.recording import TranscriptSegment, SpeakerEnum


class AudioService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
    
    async def save_audio_file(self, file_content: bytes, filename: str) -> str:
        """Save audio file to disk and return file path"""
        # Ensure upload directory exists
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_path = upload_dir / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return str(file_path)
    
    async def transcribe_audio(self, recording: Recording, db: Session) -> Optional[str]:
        """Transcribe audio file using OpenAI Whisper"""
        if not settings.OPENAI_API_KEY:
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
                transcript = openai.Audio.transcribe(
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
            
            return transcript_text
            
        except Exception as e:
            recording.status = RecordingStatusEnum.FAILED
            recording.processing_error = str(e)
            db.commit()
            return None
    
    async def perform_speaker_diarization(self, recording: Recording, db: Session) -> bool:
        """Perform speaker diarization (placeholder for future implementation)"""
        # This is a placeholder for speaker diarization functionality
        # In a real implementation, you would use libraries like pyannote.audio
        # or external services for speaker diarization
        
        if not settings.ENABLE_SPEAKER_DIARIZATION:
            return False
        
        try:
            # Placeholder logic
            # In reality, this would process the audio file and identify speakers
            # For now, we'll just update segments with alternating speakers as a demo
            
            if recording.transcript_segments:
                for i, segment in enumerate(recording.transcript_segments):
                    # Simple alternating speaker assignment (demo purposes only)
                    segment['speaker'] = SpeakerEnum.PRACTITIONER if i % 2 == 0 else SpeakerEnum.PATIENT
                
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Speaker diarization failed: {str(e)}")
            return False
    
    def validate_audio_file(self, filename: str) -> bool:
        """Validate if the file is an allowed audio format"""
        file_extension = filename.lower().split('.')[-1]
        return file_extension in settings.ALLOWED_AUDIO_EXTENSIONS
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)


audio_service = AudioService()