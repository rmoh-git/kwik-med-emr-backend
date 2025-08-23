import time
from typing import Optional, List
from sqlalchemy.orm import Session
import openai

from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatusEnum, AnalysisTypeEnum
from app.models.session import Session as SessionModel
from app.models.recording import Recording
from app.models.patient import Patient
from app.schemas.analysis import AnalysisResult, DiagnosisRecommendation, TreatmentRecommendation


class AnalysisService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
    
    def _build_context_prompt(self, session: SessionModel, include_history: bool = True) -> str:
        """Build context prompt for AI analysis"""
        context_parts = []
        
        # Patient information
        patient = session.patient
        context_parts.append(f"""
PATIENT INFORMATION:
- Name: {patient.first_name} {patient.last_name}
- Age: {self._calculate_age(patient.date_of_birth)} years old
- Gender: {patient.gender.value}
- Medical Record Number: {patient.medical_record_number or 'N/A'}
""")
        
        # Current session information
        context_parts.append(f"""
CURRENT SESSION:
- Visit Type: {session.visit_type}
- Chief Complaint: {session.chief_complaint or 'Not specified'}
- Practitioner: {session.practitioner_name}
- Session Notes: {session.notes or 'No notes'}
""")
        
        # Get transcript from current session
        current_transcript = self._get_session_transcript(session)
        if current_transcript:
            context_parts.append(f"""
CONVERSATION TRANSCRIPT:
{current_transcript}
""")
        
        # Include patient history if requested
        if include_history:
            history = self._get_patient_history(patient, exclude_session_id=session.id)
            if history:
                context_parts.append(f"""
PATIENT HISTORY:
{history}
""")
        
        return "\n".join(context_parts)
    
    def _get_session_transcript(self, session: SessionModel) -> Optional[str]:
        """Get the most recent transcript from session recordings"""
        recording = session.recordings[0] if session.recordings else None
        if recording and recording.transcript:
            return recording.transcript
        return None
    
    def _get_patient_history(self, patient: Patient, exclude_session_id) -> str:
        """Get patient's previous session history"""
        history_parts = []
        
        # Get previous sessions (excluding current one)
        previous_sessions = [s for s in patient.sessions 
                           if s.id != exclude_session_id and s.status.value == "completed"]
        
        # Sort by date (most recent first)
        previous_sessions.sort(key=lambda x: x.created_at, reverse=True)
        
        for session in previous_sessions[:5]:  # Limit to last 5 sessions
            history_parts.append(f"""
Previous Visit ({session.created_at.strftime('%Y-%m-%d')}):
- Visit Type: {session.visit_type}
- Chief Complaint: {session.chief_complaint or 'Not specified'}
- Notes: {session.notes or 'No notes'}
""")
            
            # Add previous analyses if available
            for analysis in session.analyses:
                if analysis.status == AnalysisStatusEnum.COMPLETED and analysis.result:
                    result = analysis.result
                    if isinstance(result, dict) and 'summary' in result:
                        history_parts.append(f"- Analysis Summary: {result['summary']}")
        
        return "\n".join(history_parts) if history_parts else "No previous medical history available."
    
    def _calculate_age(self, birth_date) -> int:
        """Calculate age from birth date"""
        from datetime import datetime
        today = datetime.now()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    async def perform_analysis(self, analysis: Analysis, db: Session) -> bool:
        """Perform AI analysis using OpenAI"""
        if not settings.OPENAI_API_KEY:
            analysis.status = AnalysisStatusEnum.FAILED
            analysis.error_message = "OpenAI API key not configured"
            db.commit()
            return False
        
        try:
            start_time = time.time()
            analysis.status = AnalysisStatusEnum.PROCESSING
            db.commit()
            
            # Get session and build context
            session = db.query(SessionModel).filter(SessionModel.id == analysis.session_id).first()
            if not session:
                raise Exception("Session not found")
            
            # Build context prompt
            context = self._build_context_prompt(session, include_history=True)
            
            # Create analysis prompt based on type
            system_prompt = self._get_system_prompt(analysis.analysis_type)
            user_prompt = f"{context}\n\n{analysis.prompt_context or ''}"
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Process response
            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            processing_time = time.time() - start_time
            
            # Parse and structure the response
            analysis_result = self._parse_ai_response(ai_response, analysis.analysis_type)
            
            # Update analysis record
            analysis.result = analysis_result.dict() if analysis_result else {"summary": ai_response}
            analysis.status = AnalysisStatusEnum.COMPLETED
            analysis.tokens_used = tokens_used
            analysis.processing_time_seconds = processing_time
            analysis.error_message = None
            
            db.commit()
            return True
            
        except Exception as e:
            analysis.status = AnalysisStatusEnum.FAILED
            analysis.error_message = str(e)
            db.commit()
            return False
    
    def _get_system_prompt(self, analysis_type: AnalysisTypeEnum) -> str:
        """Get system prompt based on analysis type"""
        base_prompt = """You are an AI medical assistant helping healthcare providers analyze patient encounters. 
Provide helpful insights while being clear about limitations and the need for professional medical judgment."""
        
        if analysis_type == AnalysisTypeEnum.DIAGNOSIS_ASSISTANCE:
            return f"""{base_prompt}

Focus on:
- Identifying potential diagnoses based on symptoms and history
- Providing confidence levels for each diagnosis
- Suggesting relevant ICD-10 codes where appropriate
- Highlighting important clinical findings
- Noting any red flags or urgent concerns

Always emphasize that this is clinical decision support and not a replacement for professional medical judgment."""
            
        elif analysis_type == AnalysisTypeEnum.TREATMENT_RECOMMENDATION:
            return f"""{base_prompt}

Focus on:
- Evidence-based treatment recommendations
- Prioritizing treatments by urgency and effectiveness
- Identifying potential contraindications
- Suggesting monitoring parameters
- Recommending lifestyle modifications where appropriate

Always emphasize the importance of individualized patient care and professional oversight."""
            
        elif analysis_type == AnalysisTypeEnum.FOLLOW_UP_PLANNING:
            return f"""{base_prompt}

Focus on:
- Appropriate follow-up timing
- Necessary tests or monitoring
- Patient education needs
- Referral recommendations
- Care coordination requirements

Provide specific, actionable follow-up plans."""
            
        else:  # GENERAL_ANALYSIS
            return f"""{base_prompt}

Provide a comprehensive analysis including:
- Key clinical findings
- Potential diagnoses with confidence levels
- Treatment recommendations
- Follow-up planning
- Any urgent concerns or red flags

Structure your response clearly and provide actionable insights."""
    
    def _parse_ai_response(self, response: str, analysis_type: AnalysisTypeEnum) -> Optional[AnalysisResult]:
        """Parse AI response into structured format (simplified version)"""
        try:
            # This is a simplified parser. In a production system, you would want
            # more sophisticated parsing, possibly using structured output from the AI
            
            # For now, just create a basic structure
            lines = response.split('\n')
            summary = response[:500] + "..." if len(response) > 500 else response
            
            # Extract key findings (lines that start with bullet points or dashes)
            key_findings = []
            for line in lines:
                line = line.strip()
                if line.startswith(('•', '-', '*')) and len(line) > 5:
                    key_findings.append(line.lstrip('•-* '))
            
            # Create basic analysis result
            return AnalysisResult(
                summary=summary,
                key_findings=key_findings[:10],  # Limit to 10 findings
                confidence_score=0.8  # Default confidence
            )
            
        except Exception as e:
            print(f"Failed to parse AI response: {str(e)}")
            return None


analysis_service = AnalysisService()