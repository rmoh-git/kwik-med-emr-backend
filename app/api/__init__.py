from fastapi import APIRouter
from app.api.endpoints import patients, practitioners, sessions, recordings, analysis, patient_timeline, consultations

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(practitioners.router, prefix="/practitioners", tags=["practitioners"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"]) 
api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(patient_timeline.router, prefix="/patients", tags=["patient-timeline"])
api_router.include_router(consultations.router, prefix="/consultations", tags=["consultations"])