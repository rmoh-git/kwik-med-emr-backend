"""
Simple RAG Helper for Real-time Whisper Agent
Provides MOH guidelines context to enhance AI suggestions
"""
import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger("rag-helper")

class SimpleRAGHelper:
    """Lightweight RAG helper for real-time whisper agent"""
    
    def __init__(self):
        self.pdf_processor = None
        self.guidelines_loaded = False
        self.rag_available = False
        
        # Try to initialize RAG components
        self._initialize_rag()
    
    def _initialize_rag(self):
        """Initialize RAG components if available"""
        try:
            # Check if PDF exists
            pdf_path = "/Users/macbook/Documents/Projects/horizon_100/data/guidelines/moh_guidelines.pdf"
            if not Path(pdf_path).exists():
                logger.warning("MOH guidelines PDF not found - RAG disabled")
                return
            
            # Try to import and initialize
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent))
            
            from app.services.local_pdf_processor import LocalPDFProcessor
            from app.core.config import settings
            
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not found - RAG disabled")
                return
            
            self.pdf_processor = LocalPDFProcessor(pdf_path)
            self.guidelines_loaded = True
            self.rag_available = True
            logger.info("✅ RAG helper initialized with MOH guidelines")
            
        except Exception as e:
            logger.warning(f"RAG initialization failed, continuing without: {e}")
            self.rag_available = False
    
    async def search_guidelines(self, query: str, limit: int = 2) -> List[Dict]:
        """Search MOH guidelines for relevant content"""
        if not self.rag_available or not self.pdf_processor:
            return []
        
        try:
            results = self.pdf_processor.search_similar_content(query, limit)
            
            # Format for whisper agent use
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result["text"][:300] + "..." if len(result["text"]) > 300 else result["text"],
                    "source": "Rwanda MOH Guidelines",
                    "relevance": result.get("similarity_score", 0.0)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Guidelines search failed: {e}")
            return []
    
    def extract_medical_keywords(self, text: str) -> List[str]:
        """Extract medical keywords from conversation text"""
        medical_terms = [
            "fever", "temperature", "pain", "headache", "cough", "shortness of breath",
            "nausea", "vomiting", "diarrhea", "fatigue", "weakness", "dizziness",
            "chest pain", "abdominal pain", "rash", "infection", "symptoms",
            "diagnosis", "treatment", "medication", "prescription", "dosage",
            "blood pressure", "diabetes", "malaria", "pneumonia", "tuberculosis",
            "hiv", "aids", "pregnancy", "delivery", "vaccination", "immunization"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for term in medical_terms:
            if term in text_lower:
                found_keywords.append(term)
        
        return found_keywords[:5]  # Limit to top 5 keywords
    
    async def enhance_ai_prompt(self, original_prompt: str, conversation_text: str) -> str:
        """Enhance AI prompt with RAG context if available"""
        if not self.rag_available:
            return original_prompt
        
        try:
            # Extract medical keywords from conversation
            keywords = self.extract_medical_keywords(conversation_text)
            
            if not keywords:
                return original_prompt
            
            # Search for relevant guidelines
            search_query = " ".join(keywords)
            guidelines = await self.search_guidelines(search_query)
            
            if not guidelines:
                return original_prompt
            
            # Add RAG context to prompt
            rag_context = "\n\nRELEVANT MOH GUIDELINES:\n"
            for guideline in guidelines:
                rag_context += f"- {guideline['content']}\n"
            
            enhanced_prompt = original_prompt.replace(
                "Keep under 80 words. Only suggest if valuable.",
                f"{rag_context}\nConsider the above MOH guidelines when making suggestions. Keep under 80 words. Only suggest if valuable."
            )
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            return original_prompt

# Global RAG helper instance
rag_helper = SimpleRAGHelper()