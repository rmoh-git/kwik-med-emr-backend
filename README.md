# Horizon 1000 Health Provider API

AI-powered health provider application for the Horizon 1000 initiative. This FastAPI backend provides comprehensive patient management, session tracking, audio recording/transcription, and AI-powered medical analysis capabilities.

## Features

- **Patient Registration & Management**: Create, search, and manage patient profiles
- **Session Management**: Track patient visits and practitioner interactions  
- **Audio Recording & Transcription**: Record conversations and generate transcripts using OpenAI Whisper
- **AI-Powered Analysis**: Generate medical insights and recommendations using GPT-4
- **Persistent History**: Maintain complete patient history across sessions for continuity of care

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
│   └── analysis_service.py # AI analysis service
└── main.py               # FastAPI application entry point
```

## Setup

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)
- PostgreSQL database
- OpenAI API key

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

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: Your OpenAI API key for transcription and analysis
- `OPENAI_MODEL`: GPT model to use (default: gpt-4)
- `UPLOAD_DIR`: Directory for storing audio files
- `MAX_FILE_SIZE`: Maximum audio file size in bytes
- `ENABLE_SPEAKER_DIARIZATION`: Enable speaker identification (future feature)

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