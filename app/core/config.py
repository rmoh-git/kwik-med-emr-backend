from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost/horizon_100",
        description="Database URL"
    )
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Horizon 1000 Health Provider API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI-powered health provider application for Horizon 1000 initiative"
    
    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="Secret key for JWT token generation"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for AI analysis")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model to use for analysis")
    
    # AssemblyAI Configuration
    ASSEMBLYAI_API_KEY: Optional[str] = Field(default=None, description="AssemblyAI API key for transcription and diarization")
    
    # File Storage
    UPLOAD_DIR: str = Field(default="uploads", description="Directory for file uploads")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    ALLOWED_AUDIO_EXTENSIONS: list = Field(
        default=["wav", "mp3", "m4a", "flac", "aac"],
        description="Allowed audio file extensions"
    )
    
    # Audio Processing
    WHISPER_MODEL: str = Field(default="whisper-1", description="Whisper model for transcription")
    ENABLE_SPEAKER_DIARIZATION: bool = Field(default=False, description="Enable speaker diarization")
    USE_ASSEMBLYAI: bool = Field(default=True, description="Use AssemblyAI instead of OpenAI for transcription")
    ASSEMBLYAI_SPEAKERS_EXPECTED: Optional[int] = Field(default=2, description="Expected number of speakers for diarization")
    HUGGING_FACE_TOKEN: Optional[str] = Field(default=None, description="HuggingFace token for pyannote models (deprecated)")
    
    # CORS
    BACKEND_CORS_ORIGINS: list = Field(
        default=["*"],
        description="List of allowed CORS origins"
    )
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()