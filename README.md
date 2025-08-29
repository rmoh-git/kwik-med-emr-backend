# Horizon 1000 Health Provider API

AI-powered health provider application for the Horizon 1000 initiative. This FastAPI backend provides comprehensive patient management, session tracking, audio recording/transcription, and AI-powered medical analysis capabilities.

## Features

- **Patient Registration & Management**: Create, search, and manage patient profiles
- **Session Management**: Track patient visits and practitioner interactions  
- **Real-time Audio Processing**: LiveKit-powered ambient listening with continuous speech recognition
- **AI Healthcare Agent**: Real-time AI suggestions during consultations using ambient listening
- **Audio Recording & Transcription**: Record conversations and generate transcripts using OpenAI Whisper or AssemblyAI
- **AI-Powered Analysis**: Generate medical insights and recommendations using GPT-4
- **Persistent History**: Maintain complete patient history across sessions for continuity of care
- **LiveKit Integration**: Real-time video/audio consultations with AI agent participation

## Project Structure

```
app/
├── api/                    # API layer
│   ├── endpoints/          # API route handlers
│   │   ├── patients.py     # Patient management endpoints
│   │   ├── sessions.py     # Session management endpoints  
│   │   ├── recordings.py   # Audio recording endpoints
│   │   └── analysis.py     # AI analysis endpoints
│   └── deps/              # API dependencies
├── core/                  # Core configuration
│   └── config.py          # Application settings
├── db/                    # Database layer
│   └── database.py        # Database connection and session
├── models/                # SQLAlchemy ORM models
│   ├── patient.py         # Patient database model
│   ├── session.py         # Session database model
│   ├── recording.py       # Recording database model
│   └── analysis.py        # Analysis database model
├── schemas/               # Pydantic models for API
│   ├── patient.py         # Patient API schemas
│   ├── session.py         # Session API schemas
│   ├── recording.py       # Recording API schemas
│   └── analysis.py        # Analysis API schemas
├── services/              # Business logic services
│   ├── audio_service.py   # Audio processing and transcription
│   ├── analysis_service.py # AI analysis service
│   └── livekit_service.py # LiveKit room management and tokens
└── main.py               # FastAPI application entry point

# Real-time AI Agent
realtime_whisper_agent.py  # LiveKit agent for ambient listening and AI suggestions
```

## Setup

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)
- PostgreSQL database
- OpenAI API key
- LiveKit Cloud account or self-hosted LiveKit server
- AssemblyAI API key (optional, for enhanced transcription)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd horizon_100
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Copy environment configuration:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
   - Set your database URL
   - Add your OpenAI API key
   - Configure LiveKit credentials (API key, secret, URL)
   - Add AssemblyAI API key (optional)
   - Configure other settings as needed

5. Set up the database:
```bash
# Create the database in PostgreSQL
createdb horizon_100

# Run migrations (you'll need to set up Alembic migrations)
poetry run alembic upgrade head
```

### Running the Application

```bash
# Development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the main module
poetry run python -m app.main
```

### Running the Real-time AI Agent

The LiveKit healthcare agent provides ambient listening during consultations:

```bash
# Run the real-time AI agent
poetry run python realtime_whisper_agent.py
```

The API will be available at:
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Patients
- `POST /api/v1/patients/` - Create new patient
- `GET /api/v1/patients/search` - Search patients
- `GET /api/v1/patients/{id}` - Get patient by ID
- `PUT /api/v1/patients/{id}` - Update patient
- `GET /api/v1/patients/` - List patients

### Sessions  
- `POST /api/v1/sessions/` - Create new session
- `GET /api/v1/sessions/{id}` - Get session by ID
- `PUT /api/v1/sessions/{id}` - Update session
- `POST /api/v1/sessions/{id}/end` - End session
- `GET /api/v1/sessions/patient/{id}` - Get patient sessions

### Recordings
- `POST /api/v1/recordings/start` - Start recording
- `POST /api/v1/recordings/stop` - Stop recording  
- `POST /api/v1/recordings/{id}/upload` - Upload audio file
- `POST /api/v1/recordings/{id}/transcribe` - Transcribe recording
- `GET /api/v1/recordings/{id}` - Get recording details

### Analysis
- `POST /api/v1/analysis/` - Create AI analysis
- `GET /api/v1/analysis/{id}` - Get analysis results
- `POST /api/v1/analysis/{id}/retry` - Retry failed analysis
- `GET /api/v1/analysis/session/{id}` - Get session analyses

### Consultations (LiveKit)
- `POST /api/v1/consultations/create` - Create consultation room
- `POST /api/v1/consultations/token` - Get participant token
- `POST /api/v1/consultations/{room}/end` - End consultation

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: Your OpenAI API key for transcription and analysis
- `OPENAI_MODEL`: GPT model to use (default: gpt-4)
- `UPLOAD_DIR`: Directory for storing audio files
- `MAX_FILE_SIZE`: Maximum audio file size in bytes
- `ENABLE_SPEAKER_DIARIZATION`: Enable speaker identification
- `USE_ASSEMBLYAI`: Use AssemblyAI for enhanced transcription (default: true)
- `ASSEMBLYAI_API_KEY`: Your AssemblyAI API key
- `LIVEKIT_API_KEY`: LiveKit API key for room management
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `LIVEKIT_URL`: LiveKit server URL (WebSocket)

## Architecture

### Real-time AI Healthcare Agent Architecture

The system implements an ambient listening healthcare AI using LiveKit's real-time infrastructure:

```
┌─────────────────┐    ┌───────────────────┐    ┌─────────────────────┐
│   Frontend      │    │   LiveKit Room    │    │  AI Healthcare      │
│   (React)       │◄──►│   (WebRTC)        │◄──►│  Agent (Python)     │
│                 │    │                   │    │                     │
│ • Microphone    │    │ • Audio Streams   │    │ • Whisper STT       │
│ • UI Components │    │ • Data Channels   │    │ • OpenAI Analysis   │
│ • Notifications │    │ • Participant Mgmt│    │ • Smart Filtering   │
└─────────────────┘    └───────────────────┘    └─────────────────────┘
         │                       │                         │
         │              ┌────────▼────────┐               │
         └──────────────►│  FastAPI Backend │◄─────────────┘
                         │                 │
                         │ • Session Mgmt  │
                         │ • Patient Data  │
                         │ • Room Tokens   │
                         │ • Recording API │
                         └─────────────────┘
```

### Data Flow

1. **Consultation Start**:
   - Frontend creates consultation room via API
   - Backend generates LiveKit room and tokens
   - Healthcare agent joins room automatically
   - Practitioner connects with microphone

2. **Ambient Listening**:
   - Real-time audio streams to AI agent via WebRTC
   - Agent continuously processes speech with Whisper
   - Smart filtering determines when to surface suggestions
   - AI suggestions sent via LiveKit data channels

3. **Real-time Communication**:
   - Frontend receives suggestions, transcriptions, status updates
   - User-friendly error handling for connection issues
   - Automatic recovery from transient failures

4. **Message Types**:
   - `ai_suggestion`: Medical insights and recommendations
   - `transcription`: Real-time speech-to-text
   - `agent_status`: Connection and processing status
   - `agent_error`: User-friendly error messages

### Key Components

#### RealTimeWhisperAgent (`realtime_whisper_agent.py`)
- **Ambient Processing**: Continuously processes all speech
- **Smart Filtering**: Only surfaces high-value suggestions
- **Error Handling**: Graceful failure handling with user feedback
- **Patient Context**: Integrates patient history for relevant suggestions

#### Frontend Integration (`useLiveKitRecording.ts`)
- **LiveKit Client**: Manages WebRTC connections and audio streams
- **Data Channel Handling**: Processes AI messages with proper decoding
- **UI State Management**: Real-time updates for suggestions and status
- **Error Display**: User-friendly error notifications

#### LiveKit Service (`livekit_service.py`)
- **Room Management**: Creates and manages consultation rooms
- **Token Generation**: Secure participant authentication
- **Agent Deployment**: Automatically deploys AI agents to rooms

### Ambient Listening Philosophy

The system implements true "ambient listening":
- **Always Processing**: Every word is analyzed, not just keywords
- **Smart Surfacing**: Suggestions filtered by confidence, relevance, and timing
- **Non-intrusive**: AI suggests rather than interrupts
- **Context-aware**: Uses patient history and conversation flow

## Development

### Code Quality

```bash
# Format code
poetry run black app/

# Sort imports  
poetry run isort app/

# Type checking
poetry run mypy app/

# Linting
poetry run flake8 app/
```

### Testing

```bash
# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=app
```

## Production Deployment

1. Set `ENVIRONMENT=production` in your environment
2. Use a production WSGI server like Gunicorn:
```bash
poetry run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
3. Set up proper database migrations with Alembic
4. Configure proper logging and monitoring
5. Set up file storage (local or cloud-based)
6. Implement proper authentication and authorization

## License

This project is part of the Horizon 1000 technical assessment.