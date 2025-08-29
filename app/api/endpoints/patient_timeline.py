"""
Patient Timeline API Endpoints
Provides comprehensive patient timeline with visual metrics and structured responses.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps.database import get_database
from app.services.patient_timeline_service import patient_timeline_service

router = APIRouter()


@router.get("/{patient_id}/timeline", response_model=Dict[str, Any])
async def get_patient_timeline(
    patient_id: UUID,
    days_back: int = Query(default=90, ge=1, le=365, description="Number of days to include in timeline"),
    db: Session = Depends(get_database)
):
    """
    Get comprehensive patient timeline with visual metrics and structured responses.
    
    Features:
    - Timeline events with visual data points
    - Health metrics and trends
    - Source-attributed medical insights
    - Structured recommendations
    - Visual charts data for frontend rendering
    """
    try:
        timeline_data = patient_timeline_service.generate_comprehensive_timeline(
            str(patient_id), db, days_back
        )
        
        if "error" in timeline_data:
            if "not found" in timeline_data["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=timeline_data["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Timeline generation failed: {timeline_data['error']}"
                )
        
        return timeline_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate patient timeline: {str(e)}"
        )


@router.get("/{patient_id}/timeline/metrics", response_model=Dict[str, Any])
async def get_patient_metrics(
    patient_id: UUID,
    days_back: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_database)
):
    """
    Get only the health metrics and trends for a patient.
    Lighter endpoint for dashboard widgets.
    """
    try:
        timeline_data = patient_timeline_service.generate_comprehensive_timeline(
            str(patient_id), db, days_back
        )
        
        if "error" in timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in timeline_data["error"] else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=timeline_data["error"]
            )
        
        # Return only metrics and trends
        return {
            "patient_id": str(patient_id),
            "health_metrics": timeline_data.get("health_metrics", []),
            "health_trends": timeline_data.get("health_trends", {}),
            "statistics": timeline_data.get("statistics", {}),
            "generated_at": timeline_data.get("generated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient metrics: {str(e)}"
        )


@router.get("/{patient_id}/timeline/visual-data", response_model=Dict[str, Any])
async def get_patient_visual_data(
    patient_id: UUID,
    days_back: int = Query(default=90, ge=1, le=365),
    chart_type: Optional[str] = Query(default=None, description="Filter by chart type: timeline, scatter, line"),
    db: Session = Depends(get_database)
):
    """
    Get visual data points for patient timeline charts.
    Optimized for frontend chart libraries.
    """
    try:
        timeline_data = patient_timeline_service.generate_comprehensive_timeline(
            str(patient_id), db, days_back
        )
        
        if "error" in timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in timeline_data["error"] else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=timeline_data["error"]
            )
        
        visual_data = timeline_data.get("visual_data", [])
        
        # Filter by chart type if specified
        if chart_type:
            visual_data = [chart for chart in visual_data if chart.get("chart_type") == chart_type]
        
        return {
            "patient_id": str(patient_id),
            "visual_data": visual_data,
            "chart_types_available": list(set(chart.get("chart_type") for chart in timeline_data.get("visual_data", []))),
            "generated_at": timeline_data.get("generated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get visual data: {str(e)}"
        )


@router.get("/{patient_id}/timeline/summary", response_model=Dict[str, Any])
async def get_patient_timeline_summary(
    patient_id: UUID,
    days_back: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_database)
):
    """
    Get structured summary of patient timeline.
    Includes key insights, recommendations, and next actions.
    """
    try:
        timeline_data = patient_timeline_service.generate_comprehensive_timeline(
            str(patient_id), db, days_back
        )
        
        if "error" in timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in timeline_data["error"] else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=timeline_data["error"]
            )
        
        return {
            "patient_id": str(patient_id),
            "patient_info": timeline_data.get("patient_info", {}),
            "timeline_period": timeline_data.get("timeline_period", {}),
            "structured_summary": timeline_data.get("structured_summary", {}),
            "statistics": timeline_data.get("statistics", {}),
            "generated_at": timeline_data.get("generated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline summary: {str(e)}"
        )