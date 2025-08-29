from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class AnalysisStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTypeEnum(str, Enum):
    DIAGNOSIS_ASSISTANCE = "diagnosis_assistance"
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    FOLLOW_UP_PLANNING = "follow_up_planning"
    GENERAL_ANALYSIS = "general_analysis"


class DiagnosisRecommendation(BaseModel):
    condition: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    icd_10_code: Optional[str] = None
    severity: Optional[str] = None


class TreatmentRecommendation(BaseModel):
    treatment: str
    priority: str = Field(..., description="high, medium, low")
    reasoning: str
    contraindications: Optional[List[str]] = None


class AnalysisResult(BaseModel):
    summary: str
    key_findings: Optional[List[str]] = None  # Made optional for backward compatibility
    diagnoses: Optional[List[DiagnosisRecommendation]] = None
    treatments: Optional[List[TreatmentRecommendation]] = None
    follow_up_recommendations: Optional[List[str]] = None
    red_flags: Optional[List[str]] = None
    additional_tests_needed: Optional[List[str]] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class AnalysisBase(BaseModel):
    session_id: UUID
    prompt_context: Optional[str] = None


class AnalysisCreate(AnalysisBase):
    pass


class AnalysisUpdate(BaseModel):
    status: Optional[AnalysisStatusEnum] = None
    result: Optional[AnalysisResult] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time_seconds: Optional[float] = None


class AnalysisResponse(AnalysisBase):
    id: UUID
    status: AnalysisStatusEnum
    result: Optional[AnalysisResult] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total: int
    limit: int
    offset: int


class AnalysisRequest(BaseModel):
    session_id: UUID
    include_patient_history: bool = Field(default=True)
    custom_prompt: Optional[str] = None