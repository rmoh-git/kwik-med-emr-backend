from fastapi import APIRouter
from app.api.endpoints import patients, sessions, recordings, analysis

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"]) 
api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])