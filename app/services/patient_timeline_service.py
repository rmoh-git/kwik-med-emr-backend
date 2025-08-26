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
            # Add session event
            session_event = {
                "id": f"session_{session.id}",
                "timestamp": session.created_at.isoformat(),
                "event_type": TimelineEventType.SESSION.value,
                "title": f"{session.visit_type} Session",
                "description": f"Session with {session.practitioner_name}",
                "severity": "medium",
                "duration_minutes": self._calculate_session_duration(session),
                "metadata": {
                    "session_id": str(session.id),
                    "practitioner": session.practitioner_name,
                    "visit_type": session.visit_type,
                    "status": session.status.value,
                    "notes": session.notes or ""
                },
                "recordings": len(session.recordings),
                "analyses": len(session.analyses)
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
        """Generate health metrics from patient sessions and analyses"""
        metrics = []
        
        if not sessions:
            return metrics
        
        # Session frequency metric
        session_count = len([s for s in sessions if s.status == SessionStatusEnum.COMPLETED])
        days_span = (sessions[0].created_at - sessions[-1].created_at).days or 1
        session_frequency = session_count / (days_span / 7)  # sessions per week
        
        metrics.append({
            "name": "Session Frequency",
            "value": round(session_frequency, 2),
            "unit": "sessions/week",
            "trend": self._determine_trend(session_frequency, 1.0, 2.0),  # 1-2 sessions/week is good
            "category": "engagement",
            "description": "Frequency of healthcare visits"
        })
        
        # Analysis completion rate
        total_analyses = sum(len(s.analyses) for s in sessions)
        completed_analyses = sum(len([a for a in s.analyses if a.status == AnalysisStatusEnum.COMPLETED]) for s in sessions)
        completion_rate = (completed_analyses / total_analyses * 100) if total_analyses > 0 else 0
        
        metrics.append({
            "name": "Analysis Completion Rate",
            "value": round(completion_rate, 1),
            "unit": "percentage",
            "trend": self._determine_trend(completion_rate, 80.0, 95.0),
            "category": "quality",
            "description": "Percentage of successful medical analyses"
        })
        
        # Source attribution rate (healthcare compliance metric)
        attributed_analyses = sum(
            len([a for a in s.analyses 
                if a.status == AnalysisStatusEnum.COMPLETED and 
                   a.result and a.result.get("attribution_verified", False)])
            for s in sessions
        )
        attribution_rate = (attributed_analyses / completed_analyses * 100) if completed_analyses > 0 else 0
        
        metrics.append({
            "name": "Medical Source Attribution Rate",
            "value": round(attribution_rate, 1),
            "unit": "percentage",
            "trend": HealthTrend.IMPROVING if attribution_rate > 90 else HealthTrend.STABLE,
            "category": "compliance",
            "description": "Percentage of analyses with proper medical source citations",
            "compliance_critical": True
        })
        
        # Average processing time
        processing_times = [a.processing_time_seconds for s in sessions for a in s.analyses 
                          if a.processing_time_seconds is not None]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        metrics.append({
            "name": "Average Analysis Processing Time",
            "value": round(avg_processing_time, 2),
            "unit": "seconds",
            "trend": self._determine_trend(avg_processing_time, 10.0, 30.0, reverse=True),  # Lower is better
            "category": "performance",
            "description": "Average time to complete medical analysis"
        })
        
        # Diagnosis confidence score
        confidence_scores = [
            a.result.get("confidence_score", 0.0) for s in sessions for a in s.analyses
            if a.status == AnalysisStatusEnum.COMPLETED and a.result and "confidence_score" in a.result
        ]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        metrics.append({
            "name": "Average Diagnosis Confidence",
            "value": round(avg_confidence, 3),
            "unit": "score",
            "trend": self._determine_trend(avg_confidence, 0.7, 0.9),
            "category": "accuracy",
            "description": "Average confidence level in medical diagnoses"
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
        if session.ended_at and session.created_at:
            return int((session.ended_at - session.created_at).total_seconds() / 60)
        return None
    
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