import time
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
import openai

from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatusEnum, AnalysisTypeEnum
from app.models.session import Session as SessionModel
from app.models.recording import Recording
from app.models.patient import Patient
from app.schemas.analysis import AnalysisResult, DiagnosisRecommendation, TreatmentRecommendation

# Import healthcare RAG service for source-attributed analysis
try:
    from app.services.healthcare_rag_service import healthcare_rag_service
    HEALTHCARE_RAG_AVAILABLE = True
    logging.info("Healthcare RAG service with source attribution loaded successfully")
except ImportError as e:
    HEALTHCARE_RAG_AVAILABLE = False
    logging.warning(f"Healthcare RAG service not available: {e}")


class AnalysisService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
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
        """Perform AI analysis with mandatory source attribution using Healthcare RAG"""
        start_time = time.time()
        analysis.status = AnalysisStatusEnum.PROCESSING
        db.commit()
        
        try:
            # Get session and build context
            session = db.query(SessionModel).filter(SessionModel.id == analysis.session_id).first()
            if not session:
                raise Exception("Session not found")
            
            # Build context prompt
            context = self._build_context_prompt(session, include_history=True)
            
            # Use Healthcare RAG with source attribution if available
            if HEALTHCARE_RAG_AVAILABLE:
                logging.info(f"Using Healthcare RAG with source attribution for analysis type: {analysis.analysis_type}")
                
                full_context = f"{context}\n\nAdditional Context: {analysis.prompt_context}"
                rag_result = await healthcare_rag_service.get_comprehensive_analysis_with_sources(full_context)
                
                # Validate source attribution - CRITICAL REQUIREMENT
                if not rag_result.get('attribution_verified', False):
                    logging.error("HEALTHCARE VIOLATION: Analysis completed without source attribution!")
                    analysis.status = AnalysisStatusEnum.FAILED
                    analysis.error_message = "Medical analysis must include source attribution - requirement not met"
                    db.commit()
                    return False
                
                # Structure result with source attribution
                analysis_content = rag_result.get('diagnosis_analysis') or rag_result.get('treatment_recommendations') or rag_result.get('comprehensive_analysis', '')
                sources = rag_result.get('sources', [])
                
                # Create enhanced result with source attribution
                analysis_result = {
                    "summary": analysis_content,
                    "full_analysis": analysis_content,
                    "sources": sources,
                    "source_count": len(sources),
                    "attribution_verified": True,
                    "rag_powered": True,
                    "confidence_score": 0.9,  # High confidence due to source attribution
                    "key_findings": self._extract_key_findings_from_rag_response(analysis_content)
                }
                
                # Add source citation summary
                if sources:
                    citation_summary = "\n\nSOURCE CITATIONS:\n" + "\n".join([
                        f"[{src.get('citation_id', 'REF')}] {src.get('organization', 'Unknown')}. {src.get('title', 'Medical Reference')}. {src.get('url', 'URL not available')}"
                        for src in sources
                    ])
                    analysis_result["full_analysis"] += citation_summary
                
                logging.info(f"Healthcare RAG analysis completed with {len(sources)} sources attributed")
                
            else:
                # Fallback to basic OpenAI (with warning about missing source attribution)
                logging.warning("Healthcare RAG not available - falling back to basic OpenAI without source attribution")
                
                if not self.client:
                    analysis.status = AnalysisStatusEnum.FAILED
                    analysis.error_message = "No OpenAI client and Healthcare RAG not available"
                    db.commit()
                    return False
                
                system_prompt = self._get_system_prompt_with_source_requirement(analysis.analysis_type)
                user_prompt = f"{context}\n\n{analysis.prompt_context or ''}"
                
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                ai_response = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                
                analysis_result = {
                    "summary": ai_response,
                    "full_analysis": ai_response,
                    "sources": [],
                    "source_count": 0,
                    "attribution_verified": False,
                    "analysis_type": analysis.analysis_type.value,
                    "rag_powered": False,
                    "fallback_mode": True,
                    "warning": "Analysis completed without healthcare RAG - source attribution not verified"
                }
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update analysis record with source-attributed result
            analysis.result = analysis_result
            analysis.status = AnalysisStatusEnum.COMPLETED
            analysis.tokens_used = analysis_result.get('tokens_used', 0)
            analysis.processing_time_seconds = processing_time
            analysis.error_message = None
            
            db.commit()
            
            # Log source attribution status
            source_count = analysis_result.get('source_count', 0)
            logging.info(f"Analysis completed with {source_count} medical sources attributed")
            
            return True
            
        except Exception as e:
            logging.error(f"Analysis failed: {str(e)}", exc_info=True)
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
    
    def _get_system_prompt_with_source_requirement(self, analysis_type: AnalysisTypeEnum) -> str:
        """Enhanced system prompt that requires source attribution"""
        base_prompt = """You are an AI medical assistant helping healthcare providers analyze patient encounters. 
CRITICAL REQUIREMENT: You MUST include medical source citations for all recommendations.
Use the format: [REF-#] Organization. Title. Date. URL
Provide helpful insights while being clear about limitations and the need for professional medical judgment."""
        
        if analysis_type == AnalysisTypeEnum.DIAGNOSIS_ASSISTANCE:
            return f"""{base_prompt}

MANDATORY SOURCE ATTRIBUTION REQUIRED for:
- All potential diagnoses mentioned
- ICD-10 codes suggested  
- Clinical guidelines referenced
- Diagnostic criteria cited

Focus on:
- Identifying potential diagnoses based on symptoms and history WITH SOURCES
- Providing confidence levels for each diagnosis WITH SUPPORTING LITERATURE
- Suggesting relevant ICD-10 codes WITH OFFICIAL REFERENCES
- Highlighting important clinical findings WITH GUIDELINE CITATIONS
- Noting any red flags or urgent concerns WITH PROTOCOL SOURCES

Format: [REF-1] WHO. Clinical Diagnostic Guidelines. 2024. https://who.int/guidelines
Every medical statement must include source attribution."""
        
        elif analysis_type == AnalysisTypeEnum.TREATMENT_RECOMMENDATION:
            return f"""{base_prompt}

MANDATORY SOURCE ATTRIBUTION REQUIRED for:
- All treatment recommendations
- Drug dosage and administration guidelines
- Monitoring protocols
- Contraindication warnings

Focus on:
- Evidence-based treatment recommendations WITH CLINICAL TRIAL CITATIONS
- Prioritizing treatments by urgency and effectiveness WITH EVIDENCE LEVELS
- Identifying potential contraindications WITH PHARMACEUTICAL REFERENCES
- Suggesting monitoring parameters WITH CLINICAL PROTOCOL SOURCES
- Recommending lifestyle modifications WITH GUIDELINE CITATIONS

Format: [REF-1] CDC. Treatment Protocols. 2024. https://cdc.gov/protocols
All recommendations must cite authoritative medical sources."""
        
        elif analysis_type == AnalysisTypeEnum.FOLLOW_UP_PLANNING:
            return f"""{base_prompt}

MANDATORY SOURCE ATTRIBUTION REQUIRED for:
- Follow-up timing recommendations
- Required diagnostic tests
- Monitoring schedules
- Referral criteria

Focus on:
- Appropriate follow-up timing WITH CLINICAL GUIDELINE CITATIONS
- Necessary tests or monitoring WITH PROTOCOL REFERENCES
- Patient education needs WITH HEALTH AUTHORITY SOURCES
- Referral recommendations WITH SPECIALTY GUIDELINES
- Care coordination requirements WITH STANDARD OF CARE CITATIONS

Format: [REF-1] NHS. Follow-up Guidelines. 2024. https://nhs.uk/guidelines
Every follow-up recommendation must include source attribution."""
        
        else:  # GENERAL_ANALYSIS
            return f"""{base_prompt}

MANDATORY SOURCE ATTRIBUTION REQUIRED for ALL medical insights provided.

Provide a comprehensive analysis including:
- Key clinical findings WITH SUPPORTING LITERATURE CITATIONS
- Potential diagnoses with confidence levels WITH DIAGNOSTIC GUIDELINE SOURCES
- Treatment recommendations WITH EVIDENCE-BASED MEDICINE CITATIONS  
- Follow-up planning WITH CLINICAL PROTOCOL REFERENCES
- Any urgent concerns or red flags WITH EMERGENCY GUIDELINE SOURCES

Format: [REF-1] Medical Authority. Guideline Title. Date. URL
Structure your response clearly and provide actionable insights with complete source attribution.
NO medical advice should be given without proper source citations."""
    
    def _extract_key_findings_from_rag_response(self, analysis_content: str) -> List[str]:
        """Extract key medical findings from RAG response"""
        findings = []
        lines = analysis_content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for bullet points, numbered items, or key medical terms
            if (line.startswith(('•', '-', '*', '1.', '2.', '3.')) and 
                len(line) > 10 and 
                any(term in line.lower() for term in ['diagnosis', 'symptom', 'treatment', 'recommendation', 'finding', 'concern'])):
                # Clean the finding
                clean_finding = line.lstrip('•-*0123456789. ').strip()
                if clean_finding and len(clean_finding) < 200:  # Reasonable length
                    findings.append(clean_finding)
        
        return findings[:10]  # Limit to top 10 findings


analysis_service = AnalysisService()