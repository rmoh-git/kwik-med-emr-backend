"""
Patient Timeline Service with Visual Metrics and Structured Responses
Provides comprehensive patient progress tracking with visual data and structured analysis.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from enum import Enum
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.patient import Patient
from app.models.session import Session as SessionModel, SessionStatusEnum
from app.models.analysis import Analysis, AnalysisStatusEnum
from app.models.recording import Recording

logger = logging.getLogger(__name__)


class TimelineEventType(str, Enum):
    SESSION = "session"
    ANALYSIS = "analysis"
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    MILESTONE = "milestone"
    ALERT = "alert"


class HealthTrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class TimelineMetric:
    name: str
    value: float
    unit: str
    trend: HealthTrend
    reference_range: Optional[Tuple[float, float]] = None
    last_updated: Optional[datetime] = None


@dataclass
class VisualDataPoint:
    timestamp: datetime
    value: float
    label: str
    category: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TimelineEvent:
    id: str
    timestamp: datetime
    event_type: TimelineEventType
    title: str
    description: str
    severity: str  # low, medium, high, critical
    metadata: Dict[str, Any]
    metrics: List[TimelineMetric]
    visual_data: List[VisualDataPoint]


class PatientTimelineService:
    """
    Service for generating comprehensive patient timelines with visual metrics.
    Provides structured responses for healthcare providers to track patient progress.
    """
    
    def __init__(self):
        logger.info("Initializing Patient Timeline Service")
    
    def generate_comprehensive_timeline(self, patient_id: str, db: Session, 
                                       days_back: int = 90) -> Dict[str, Any]:
        """Generate comprehensive patient timeline with visual metrics and structured responses"""
        logger.info(f"Generating comprehensive timeline for patient {patient_id}")
        
        try:
            # Get patient and validate
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Get patient sessions within date range
            sessions = db.query(SessionModel).filter(
                SessionModel.patient_id == patient_id,
                SessionModel.created_at >= start_date,
                SessionModel.created_at <= end_date
            ).order_by(desc(SessionModel.created_at)).all()
            
            # Build comprehensive timeline
            timeline_events = self._build_timeline_events(sessions, db)
            
            # Generate health metrics
            health_metrics = self._generate_health_metrics(sessions, db)
            
            # Create visual data points
            visual_data = self._create_visual_data_points(sessions, db)
            
            # Calculate health trends
            health_trends = self._calculate_health_trends(sessions, db)
            
            # Generate structured summary
            structured_summary = self._generate_structured_summary(
                patient, sessions, health_metrics, health_trends
            )
            
            # Compile comprehensive timeline response
            timeline_response = {
                "patient_info": {
                    "id": str(patient.id),
                    "name": f"{patient.first_name} {patient.last_name}",
                    "age": self._calculate_age(patient.date_of_birth),
                    "gender": patient.gender.value,
                    "medical_record_number": patient.medical_record_number
                },
                "timeline_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days_covered": days_back
                },
                "timeline_events": timeline_events,
                "health_metrics": health_metrics,
                "visual_data": visual_data,
                "health_trends": health_trends,
                "structured_summary": structured_summary,
                "statistics": {
                    "total_sessions": len(sessions),
                    "completed_sessions": len([s for s in sessions if s.status == SessionStatusEnum.COMPLETED]),
                    "total_analyses": sum(len(s.analyses) for s in sessions),
                    "timeline_events_count": len(timeline_events)
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Timeline generated with {len(timeline_events)} events and {len(health_metrics)} metrics")
            return timeline_response
            
        except Exception as e:
            logger.error(f"Failed to generate patient timeline: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "patient_id": patient_id,
                "generated_at": datetime.now().isoformat()
            }
    
    def _build_timeline_events(self, sessions: List[SessionModel], db: Session) -> List[Dict[str, Any]]:
        """Build structured timeline events from patient sessions"""
        events = []
        
        for session in sessions:
            # Add session event with clinical focus
            duration = self._calculate_session_duration(session)
            session_event = {
                "id": f"session_{session.id}",
                "timestamp": session.created_at.isoformat(),
                "event_type": TimelineEventType.SESSION.value,
                "title": f"{session.visit_type} - {session.practitioner_name}",
                "description": self._extract_clinical_summary(session),
                "severity": self._assess_session_priority(session),
                "duration_minutes": duration,
                "clinical_details": {
                    "visit_type": session.visit_type,
                    "duration": f"{duration} minutes" if duration else "Not specified",
                    "documented": "Yes" if session.recordings else "No",
                    "follow_up_noted": "Yes" if (session.notes and 
                        any(word in session.notes.lower() for word in ['follow-up', 'return', 'next visit'])) else "No",
                    "practitioner": session.practitioner_name,
                    "status": "Completed" if session.status == SessionStatusEnum.COMPLETED else session.status.value
                }
            }
            events.append(session_event)
            
            # Add analysis events
            for analysis in session.analyses:
                if analysis.status == AnalysisStatusEnum.COMPLETED and analysis.result:
                    analysis_event = {
                        "id": f"analysis_{analysis.id}",
                        "timestamp": analysis.created_at.isoformat(),
                        "event_type": TimelineEventType.ANALYSIS.value,
                        "title": f"{analysis.analysis_type.value.replace('_', ' ').title()} Analysis",
                        "description": self._extract_analysis_summary(analysis.result),
                        "severity": self._determine_analysis_severity(analysis.result),
                        "metadata": {
                            "analysis_id": str(analysis.id),
                            "session_id": str(session.id),
                            "analysis_type": analysis.analysis_type.value,
                            "processing_time": analysis.processing_time_seconds,
                            "tokens_used": analysis.tokens_used,
                            "confidence_score": analysis.result.get("confidence_score", 0.0),
                            "source_attributed": analysis.result.get("attribution_verified", False),
                            "source_count": analysis.result.get("source_count", 0)
                        }
                    }
                    events.append(analysis_event)
        
        # Sort events by timestamp (most recent first)
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events
    
    def _generate_health_metrics(self, sessions: List[SessionModel], db: Session) -> List[Dict[str, Any]]:
        """Generate clinically meaningful health metrics for healthcare practitioners"""
        metrics = []
        
        if not sessions:
            return metrics
        
        # Total consultations completed
        completed_sessions = [s for s in sessions if s.status == SessionStatusEnum.COMPLETED]
        metrics.append({
            "name": "Total Consultations",
            "value": len(completed_sessions),
            "unit": "visits",
            "trend": HealthTrend.STABLE.value,
            "category": "care_access",
            "description": "Number of completed medical consultations"
        })
        
        # Average consultation duration
        session_durations = [self._calculate_session_duration(s) for s in completed_sessions 
                           if self._calculate_session_duration(s) is not None]
        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 30
        
        metrics.append({
            "name": "Average Consultation Duration",
            "value": round(avg_duration),
            "unit": "minutes",
            "trend": self._determine_trend(avg_duration, 20, 45),  # 20-45 minutes is typical
            "category": "care_quality",
            "description": "Average length of medical consultations"
        })
        
        # Days since last visit
        if completed_sessions:
            # Handle timezone-aware datetime comparison
            now = datetime.now()
            last_session_time = completed_sessions[0].created_at
            
            # Make both datetimes timezone-naive for comparison
            if last_session_time.tzinfo is not None:
                last_session_time = last_session_time.replace(tzinfo=None)
            if now.tzinfo is not None:
                now = now.replace(tzinfo=None)
                
            days_since_last = (now - last_session_time).days
            metrics.append({
                "name": "Days Since Last Visit",
                "value": days_since_last,
                "unit": "days",
                "trend": self._determine_trend(days_since_last, 30, 90, reverse=True),  # Less days is better
                "category": "follow_up",
                "description": "Time elapsed since most recent consultation"
            })
        
        # Visit frequency (visits per month)
        if len(completed_sessions) > 1:
            total_days = (completed_sessions[0].created_at - completed_sessions[-1].created_at).days
            if total_days > 0:
                visits_per_month = (len(completed_sessions) * 30) / total_days
                metrics.append({
                    "name": "Visit Frequency",
                    "value": round(visits_per_month, 1),
                    "unit": "visits/month",
                    "trend": self._determine_trend(visits_per_month, 1.0, 3.0),  # 1-3 visits per month
                    "category": "engagement",
                    "description": "Frequency of healthcare consultations"
                })
        
        # Follow-up compliance (based on session notes mentioning follow-up)
        sessions_with_followup = len([s for s in completed_sessions 
                                    if s.notes and any(keyword in s.notes.lower() 
                                    for keyword in ['follow-up', 'follow up', 'return', 'next visit'])])
        followup_rate = (sessions_with_followup / len(completed_sessions) * 100) if completed_sessions else 0
        
        metrics.append({
            "name": "Follow-up Rate",
            "value": round(followup_rate, 1),
            "unit": "percentage",
            "trend": self._determine_trend(followup_rate, 70, 90),  # 70-90% follow-up rate is good
            "category": "care_continuity",
            "description": "Percentage of consultations with follow-up plans"
        })
        
        # Recording completion rate (clinical documentation)
        sessions_with_recordings = len([s for s in completed_sessions if s.recordings])
        recording_rate = (sessions_with_recordings / len(completed_sessions) * 100) if completed_sessions else 0
        
        metrics.append({
            "name": "Documentation Rate",
            "value": round(recording_rate, 1),
            "unit": "percentage",
            "trend": self._determine_trend(recording_rate, 80, 95),
            "category": "documentation",
            "description": "Percentage of consultations with audio documentation"
        })
        
        return metrics
    
    def _create_visual_data_points(self, sessions: List[SessionModel], db: Session) -> List[Dict[str, Any]]:
        """Create visual data points for charts and graphs"""
        visual_data = []
        
        # Session timeline data points
        session_points = []
        for session in sessions:
            session_points.append({
                "timestamp": session.created_at.isoformat(),
                "value": 1,  # Session occurred
                "label": f"{session.visit_type}",
                "category": "sessions",
                "metadata": {
                    "practitioner": session.practitioner_name,
                    "status": session.status.value,
                    "duration": self._calculate_session_duration(session)
                }
            })
        
        visual_data.append({
            "chart_type": "timeline",
            "title": "Session History",
            "data_points": session_points,
            "y_axis_label": "Sessions",
            "color_scheme": "blue"
        })
        
        # Analysis completion over time
        analysis_points = []
        for session in sessions:
            for analysis in session.analyses:
                if analysis.status == AnalysisStatusEnum.COMPLETED:
                    analysis_points.append({
                        "timestamp": analysis.created_at.isoformat(),
                        "value": analysis.result.get("confidence_score", 0.8),
                        "label": analysis.analysis_type.value.replace("_", " ").title(),
                        "category": "analysis_confidence",
                        "metadata": {
                            "processing_time": analysis.processing_time_seconds,
                            "tokens_used": analysis.tokens_used,
                            "source_count": analysis.result.get("source_count", 0)
                        }
                    })
        
        visual_data.append({
            "chart_type": "scatter",
            "title": "Analysis Confidence Over Time",
            "data_points": analysis_points,
            "y_axis_label": "Confidence Score",
            "color_scheme": "green"
        })
        
        # Source attribution trend
        attribution_points = []
        monthly_data = {}
        for session in sessions:
            month_key = session.created_at.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {"total": 0, "attributed": 0}
            
            for analysis in session.analyses:
                if analysis.status == AnalysisStatusEnum.COMPLETED:
                    monthly_data[month_key]["total"] += 1
                    if analysis.result and analysis.result.get("attribution_verified", False):
                        monthly_data[month_key]["attributed"] += 1
        
        for month, data in monthly_data.items():
            attribution_rate = (data["attributed"] / data["total"] * 100) if data["total"] > 0 else 0
            attribution_points.append({
                "timestamp": f"{month}-01T00:00:00",
                "value": attribution_rate,
                "label": f"{month}",
                "category": "source_attribution",
                "metadata": {
                    "total_analyses": data["total"],
                    "attributed_analyses": data["attributed"]
                }
            })
        
        visual_data.append({
            "chart_type": "line",
            "title": "Medical Source Attribution Trend",
            "data_points": attribution_points,
            "y_axis_label": "Attribution Rate (%)",
            "color_scheme": "red",
            "compliance_critical": True
        })
        
        return visual_data
    
    def _calculate_health_trends(self, sessions: List[SessionModel], db: Session) -> Dict[str, Any]:
        """Calculate health trends based on session patterns and analysis results"""
        if len(sessions) < 2:
            return {"overall_trend": HealthTrend.UNKNOWN.value, "trend_analysis": "Insufficient data"}
        
        trends = {}
        
        # Session frequency trend
        recent_sessions = sessions[:len(sessions)//2] if len(sessions) > 4 else sessions[:2]
        older_sessions = sessions[len(sessions)//2:] if len(sessions) > 4 else sessions[2:]
        
        recent_freq = len(recent_sessions) / max((recent_sessions[0].created_at - recent_sessions[-1].created_at).days, 1)
        older_freq = len(older_sessions) / max((older_sessions[0].created_at - older_sessions[-1].created_at).days, 1) if older_sessions else 0
        
        if recent_freq > older_freq * 1.2:
            trends["session_frequency"] = HealthTrend.IMPROVING.value
        elif recent_freq < older_freq * 0.8:
            trends["session_frequency"] = HealthTrend.DECLINING.value
        else:
            trends["session_frequency"] = HealthTrend.STABLE.value
        
        # Analysis quality trend
        recent_analyses = [a for s in recent_sessions for a in s.analyses if a.status == AnalysisStatusEnum.COMPLETED]
        older_analyses = [a for s in older_sessions for a in s.analyses if a.status == AnalysisStatusEnum.COMPLETED]
        
        recent_confidence = sum(a.result.get("confidence_score", 0.8) for a in recent_analyses if a.result) / len(recent_analyses) if recent_analyses else 0
        older_confidence = sum(a.result.get("confidence_score", 0.8) for a in older_analyses if a.result) / len(older_analyses) if older_analyses else 0
        
        if recent_confidence > older_confidence + 0.1:
            trends["analysis_quality"] = HealthTrend.IMPROVING.value
        elif recent_confidence < older_confidence - 0.1:
            trends["analysis_quality"] = HealthTrend.DECLINING.value
        else:
            trends["analysis_quality"] = HealthTrend.STABLE.value
        
        # Overall trend determination
        trend_values = list(trends.values())
        if HealthTrend.DECLINING.value in trend_values:
            overall_trend = HealthTrend.DECLINING.value
        elif all(t == HealthTrend.IMPROVING.value for t in trend_values):
            overall_trend = HealthTrend.IMPROVING.value
        else:
            overall_trend = HealthTrend.STABLE.value
        
        trends["overall_trend"] = overall_trend
        trends["trend_analysis"] = self._generate_trend_analysis(trends, sessions)
        
        return trends
    
    def _generate_structured_summary(self, patient: Patient, sessions: List[SessionModel], 
                                   health_metrics: List[Dict], health_trends: Dict) -> Dict[str, Any]:
        """Generate structured summary of patient timeline"""
        
        # Key insights
        insights = []
        
        # Source attribution insight (critical for healthcare)
        attribution_metric = next((m for m in health_metrics if "Source Attribution" in m["name"]), None)
        if attribution_metric:
            if attribution_metric["value"] < 90:
                insights.append({
                    "type": "compliance_warning",
                    "severity": "high",
                    "message": f"Medical source attribution rate is {attribution_metric['value']}% - below recommended 90% threshold",
                    "recommendation": "Review analysis processes to ensure all medical recommendations include proper source citations"
                })
            else:
                insights.append({
                    "type": "compliance_success",
                    "severity": "low",
                    "message": f"Excellent medical source attribution rate of {attribution_metric['value']}%",
                    "recommendation": "Continue current practices for healthcare compliance"
                })
        
        # Session frequency insight
        session_metric = next((m for m in health_metrics if "Session Frequency" in m["name"]), None)
        if session_metric and session_metric["value"] < 0.5:
            insights.append({
                "type": "engagement_concern",
                "severity": "medium",
                "message": f"Low session frequency: {session_metric['value']} sessions per week",
                "recommendation": "Consider increasing patient engagement or follow-up frequency"
            })
        
        # Care quality assessment
        recent_analyses = [a for s in sessions[:5] for a in s.analyses if a.status == AnalysisStatusEnum.COMPLETED]
        avg_sources = sum(a.result.get("source_count", 0) for a in recent_analyses if a.result) / len(recent_analyses) if recent_analyses else 0
        
        care_quality = "excellent" if avg_sources > 3 else "good" if avg_sources > 1 else "needs_improvement"
        
        return {
            "patient_overview": {
                "total_sessions": len(sessions),
                "active_period_days": (sessions[0].created_at - sessions[-1].created_at).days if sessions else 0,
                "care_quality_rating": care_quality,
                "compliance_status": "compliant" if attribution_metric and attribution_metric["value"] > 90 else "needs_review"
            },
            "key_insights": insights,
            "recommendations": self._generate_recommendations(sessions, health_metrics, health_trends),
            "next_actions": self._suggest_next_actions(sessions, health_trends),
            "summary_generated_at": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, sessions: List[SessionModel], 
                                health_metrics: List[Dict], health_trends: Dict) -> List[str]:
        """Generate actionable recommendations based on timeline analysis"""
        recommendations = []
        
        # Source attribution recommendations
        attribution_metric = next((m for m in health_metrics if "Source Attribution" in m["name"]), None)
        if attribution_metric and attribution_metric["value"] < 95:
            recommendations.append("Enhance medical source attribution processes to improve healthcare compliance")
        
        # Session frequency recommendations
        session_metric = next((m for m in health_metrics if "Session Frequency" in m["name"]), None)
        if session_metric and session_metric["value"] < 1.0:
            recommendations.append("Consider more frequent patient monitoring or follow-up sessions")
        
        # Trend-based recommendations
        if health_trends.get("overall_trend") == HealthTrend.DECLINING.value:
            recommendations.append("Investigate factors contributing to declining health trends")
        elif health_trends.get("overall_trend") == HealthTrend.IMPROVING.value:
            recommendations.append("Continue current treatment approaches as patient shows improvement")
        
        return recommendations
    
    def _suggest_next_actions(self, sessions: List[SessionModel], health_trends: Dict) -> List[str]:
        """Suggest immediate next actions based on timeline analysis"""
        actions = []
        
        if not sessions:
            actions.append("Schedule initial patient consultation")
            return actions
        
        last_session = sessions[0]
        now = datetime.now()
        if last_session.created_at.tzinfo is not None:
            now = now.replace(tzinfo=last_session.created_at.tzinfo)
        days_since_last = (now - last_session.created_at).days
        
        if days_since_last > 30:
            actions.append("Schedule follow-up appointment - last session was over 30 days ago")
        
        # Check for incomplete analyses
        incomplete_analyses = [a for s in sessions[:3] for a in s.analyses if a.status != AnalysisStatusEnum.COMPLETED]
        if incomplete_analyses:
            actions.append(f"Review {len(incomplete_analyses)} incomplete analyses from recent sessions")
        
        # Source attribution action
        recent_analyses = [a for s in sessions[:5] for a in s.analyses if a.status == AnalysisStatusEnum.COMPLETED]
        unattributed = [a for a in recent_analyses if a.result and not a.result.get("attribution_verified", False)]
        if unattributed:
            actions.append(f"Add medical source attribution to {len(unattributed)} recent analyses")
        
        return actions
    
    # Helper methods
    def _calculate_age(self, birth_date) -> int:
        today = datetime.now().date() if isinstance(birth_date, datetime) else datetime.now()
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    def _calculate_session_duration(self, session: SessionModel) -> Optional[int]:
        """Calculate realistic session duration with constraints"""
        if session.ended_at and session.created_at:
            duration_minutes = int((session.ended_at - session.created_at).total_seconds() / 60)
            
            # Apply realistic constraints for healthcare sessions (5-120 minutes)
            if duration_minutes < 5:
                return 5  # Minimum session duration
            elif duration_minutes > 120:
                return 60  # Cap unrealistic durations at 60 minutes (typical consultation)
            else:
                return duration_minutes
        
        # If no end time, estimate from recordings or default to typical consultation
        if session.recordings:
            total_recording_duration = sum(
                r.duration_seconds or 0 for r in session.recordings 
                if r.duration_seconds and r.duration_seconds > 0
            ) / 60  # Convert to minutes
            
            if total_recording_duration > 0:
                # Session is usually 10-20% longer than recording due to setup/discussion
                estimated_duration = int(total_recording_duration * 1.15)
                return min(max(estimated_duration, 10), 90)  # Between 10-90 minutes
        
        return 30  # Default to 30 minutes for typical consultation
    
    def _extract_clinical_summary(self, session: SessionModel) -> str:
        """Extract clinically relevant summary from session"""
        if session.notes:
            # Extract first meaningful sentence from notes
            notes = session.notes.strip()
            if notes:
                first_sentence = notes.split('.')[0][:150]
                return first_sentence + "..." if len(notes) > 150 else first_sentence
        
        # Default descriptions based on visit type
        visit_descriptions = {
            "consultation": "Initial consultation and examination",
            "follow_up": "Follow-up visit to assess progress",
            "emergency": "Emergency consultation",
            "routine": "Routine check-up and assessment",
            "specialist": "Specialist consultation"
        }
        
        return visit_descriptions.get(session.visit_type, "Medical consultation")
    
    def _assess_session_priority(self, session: SessionModel) -> str:
        """Assess clinical priority/severity of session"""
        # Check for emergency indicators
        if session.visit_type == "emergency":
            return "high"
        
        # Check notes for urgent keywords
        if session.notes:
            urgent_keywords = ['urgent', 'severe', 'critical', 'emergency', 'acute', 'pain']
            if any(keyword in session.notes.lower() for keyword in urgent_keywords):
                return "high"
        
        # Follow-up visits are typically medium priority
        if session.visit_type == "follow_up":
            return "medium"
        
        return "low"  # Default for routine visits
    
    def _extract_analysis_summary(self, result: Dict) -> str:
        if "summary" in result:
            return result["summary"][:200] + "..." if len(result["summary"]) > 200 else result["summary"]
        return "Analysis completed"
    
    def _determine_analysis_severity(self, result: Dict) -> str:
        confidence = result.get("confidence_score", 0.8)
        if confidence > 0.9:
            return "low"
        elif confidence > 0.7:
            return "medium"
        else:
            return "high"
    
    def _determine_trend(self, value: float, good_threshold: float, excellent_threshold: float, reverse: bool = False) -> str:
        if reverse:
            if value <= good_threshold:
                return HealthTrend.IMPROVING.value
            elif value <= excellent_threshold:
                return HealthTrend.STABLE.value
            else:
                return HealthTrend.DECLINING.value
        else:
            if value >= excellent_threshold:
                return HealthTrend.IMPROVING.value
            elif value >= good_threshold:
                return HealthTrend.STABLE.value
            else:
                return HealthTrend.DECLINING.value
    
    def _generate_trend_analysis(self, trends: Dict, sessions: List[SessionModel]) -> str:
        analysis_parts = []
        
        if trends.get("session_frequency") == HealthTrend.IMPROVING.value:
            analysis_parts.append("Patient engagement is increasing")
        elif trends.get("session_frequency") == HealthTrend.DECLINING.value:
            analysis_parts.append("Patient engagement may be declining")
        
        if trends.get("analysis_quality") == HealthTrend.IMPROVING.value:
            analysis_parts.append("Analysis quality and confidence are improving")
        elif trends.get("analysis_quality") == HealthTrend.DECLINING.value:
            analysis_parts.append("Analysis quality may need attention")
        
        if not analysis_parts:
            analysis_parts.append("Patient trends are stable")
        
        return ". ".join(analysis_parts) + "."


# Global service instance
patient_timeline_service = PatientTimelineService()