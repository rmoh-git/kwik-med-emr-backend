"""
Ultra-Simple RAG for Real-time Whisper Agent
Reads from actual MOH guidelines PDF and provides relevant context
"""
import logging
from typing import List
from pathlib import Path

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger("simple-rag")

class SimpleRAG:
    """Ultra-lightweight RAG for whisper agent"""
    
    def __init__(self):
        self.vector_db = None
        self.embedder = None
        self.vector_db_ready = False
        self.medical_keywords = {
            "fever": ["temperature", "pyrexia", "hyperthermia"],
            "pain": ["ache", "discomfort", "soreness"],  
            "infection": ["bacterial", "viral", "sepsis"],
            "respiratory": ["cough", "breathing", "pneumonia", "asthma"],
            "cardiac": ["heart", "chest pain", "hypertension"],
            "diabetes": ["blood sugar", "glucose", "insulin"],
            "malaria": ["mosquito", "fever", "chills"],
            "pregnancy": ["maternal", "delivery", "prenatal"],
            "pediatric": ["children", "infant", "vaccination"]
        }
        
        # Initialize vector database (lightweight)
        self._initialize_vector_db()
    
    def _initialize_vector_db(self):
        """Initialize vector database for querying existing embeddings"""
        try:
            # Check if we need OpenAI for embeddings
            import os
            import sys
            from pathlib import Path
            
            # Add project path
            sys.path.append(str(Path(__file__).parent))
            
            try:
                from app.core.config import settings
                openai_key = settings.OPENAI_API_KEY
            except ImportError:
                openai_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_key:
                logger.warning("OpenAI API key not found - vector search disabled")
                return
            
            # Try to initialize embedder and vector DB
            from agno.embedder.openai import OpenAIEmbedder
            from agno.vectordb.lancedb import LanceDb
            
            self.embedder = OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=openai_key
            )
            
            self.vector_db = LanceDb(
                table_name="moh_guidelines_chunks",
                embedder=self.embedder
            )
            
            self.vector_db_ready = True
            logger.info("✅ Vector database ready for MOH guidelines search")
            
        except Exception as e:
            logger.warning(f"Vector DB initialization failed: {e} - using fallback search")
            self.vector_db_ready = False
    
    def _load_guidelines_old(self):
        """Load MOH guidelines from PDF"""
        try:
            pdf_path = Path(__file__).parent / "data" / "guidelines" / "moh_guidelines.pdf"
            
            if pdf_path.exists() and (PDFPLUMBER_AVAILABLE or PYPDF_AVAILABLE):
                # Extract text from actual PDF
                self.guidelines_text = self._extract_pdf_text(pdf_path)
                if self.guidelines_text and len(self.guidelines_text) > 1000:  # Check if we got meaningful content
                    self.guidelines_available = True
                    logger.info(f"✅ Simple RAG loaded from PDF: {len(self.guidelines_text)} characters")
                else:
                    logger.warning("⚠️ PDF extraction returned minimal content - using fallback guidelines")
                    self.guidelines_text = self._get_basic_guidelines()
                    self.guidelines_available = False
            elif pdf_path.exists():
                logger.warning("⚠️ No PDF readers available - using fallback guidelines")
                self.guidelines_text = self._get_basic_guidelines()
                self.guidelines_available = False
            else:
                logger.warning("⚠️ MOH guidelines PDF not found - using fallback guidelines")
                self.guidelines_text = self._get_basic_guidelines()
                self.guidelines_available = False
                
        except Exception as e:
            logger.error(f"Guidelines loading failed: {e}")
            self.guidelines_text = self._get_basic_guidelines()
            self.guidelines_available = False
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from MOH guidelines PDF with robust error handling"""
        
        # Try pdfplumber first (more robust)
        if PDFPLUMBER_AVAILABLE:
            text_content = self._extract_with_pdfplumber(pdf_path)
            if text_content and len(text_content) > 1000:
                return text_content
        
        # Fallback to pypdf
        if PYPDF_AVAILABLE:
            text_content = self._extract_with_pypdf(pdf_path)
            if text_content and len(text_content) > 1000:
                return text_content
        
        # If both failed, use basic guidelines
        logger.error("Both PDF extraction methods failed")
        return self._get_basic_guidelines()
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """Extract text using pdfplumber (more robust for complex PDFs)"""
        try:
            text_content = ""
            pages_processed = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} total pages (using pdfplumber)")
                
                # Extract text from first 20 pages
                max_pages = min(20, len(pdf.pages))
                
                for page_num in range(max_pages):
                    try:
                        page = pdf.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            text_content += f"\n--- Page {page_num + 1} ---\n"
                            text_content += page_text.strip() + "\n"
                            pages_processed += 1
                            
                    except Exception as e:
                        logger.warning(f"pdfplumber: Failed to extract text from page {page_num + 1}: {e}")
                        continue
            
            if text_content.strip():
                logger.info(f"✅ pdfplumber extracted {len(text_content)} characters from {pages_processed}/{max_pages} pages")
                return text_content
            else:
                logger.warning("⚠️ pdfplumber: No text could be extracted")
                return ""
                
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return ""
    
    def _extract_with_pypdf(self, pdf_path: Path) -> str:
        """Extract text using pypdf (fallback method)"""
        try:
            text_content = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file, strict=False)
                
                logger.info(f"PDF has {len(pdf_reader.pages)} total pages (using pypdf)")
                
                max_pages = min(20, len(pdf_reader.pages))
                pages_processed = 0
                
                for page_num in range(max_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            text_content += f"\n--- Page {page_num + 1} ---\n"
                            text_content += page_text.strip() + "\n"
                            pages_processed += 1
                            
                    except Exception as e:
                        logger.warning(f"pypdf: Failed to extract text from page {page_num + 1}: {e}")
                        continue
            
            if text_content.strip():
                logger.info(f"✅ pypdf extracted {len(text_content)} characters from {pages_processed}/{max_pages} pages")
                return text_content
            else:
                logger.warning("⚠️ pypdf: No text could be extracted")
                return ""
            
        except Exception as e:
            logger.error(f"pypdf extraction failed: {e}")
            return ""
    
    def _get_basic_guidelines(self) -> str:
        """Basic medical guidelines for common conditions"""
        return """
        FEVER MANAGEMENT:
        - Check temperature, assess for signs of severe infection
        - Consider malaria testing in endemic areas
        - Monitor for danger signs: difficulty breathing, altered consciousness
        
        RESPIRATORY SYMPTOMS:
        - Assess breathing rate, oxygen saturation if available
        - Listen for wheeze, crackles, or diminished breath sounds
        - Consider pneumonia if fever + cough + fast breathing
        
        CHEST PAIN:
        - Assess for cardiac vs non-cardiac causes
        - Check blood pressure, pulse rate and rhythm
        - Consider ECG if available and indicated
        
        PEDIATRIC DANGER SIGNS:
        - Unable to feed/drink, persistent vomiting
        - Convulsions, unconscious/lethargic
        - Fast breathing, chest indrawing
        
        MATERNAL HEALTH:
        - Monitor blood pressure during pregnancy
        - Watch for danger signs: severe headache, blurred vision
        - Ensure skilled birth attendance
        
        GENERAL RED FLAGS:
        - Severe dehydration, shock
        - Altered mental status
        - Severe pain not responding to treatment
        """
    
    def extract_medical_keywords(self, text: str) -> List[str]:
        """Extract medical keywords from conversation"""
        text_lower = text.lower()
        found_keywords = []
        
        # Check for direct medical terms
        for category, synonyms in self.medical_keywords.items():
            if category in text_lower:
                found_keywords.append(category)
            else:
                for synonym in synonyms:
                    if synonym in text_lower:
                        found_keywords.append(category)
                        break
        
        return list(set(found_keywords))  # Remove duplicates
    
    def get_relevant_guidance(self, keywords: List[str]) -> str:
        """Get relevant guidance based on keywords using vector search"""
        if not keywords:
            return ""
        
        # Use vector database if available
        if self.vector_db_ready and self.vector_db:
            return self._search_vector_db(keywords)
        else:
            # Fallback to basic guidance
            return self._get_basic_guidance_for_keywords(keywords)
    
    def _search_vector_db(self, keywords: List[str]) -> str:
        """Search vector database for relevant content"""
        try:
            # Create search query from keywords
            search_query = " ".join(keywords)
            
            # Search vector database
            results = self.vector_db.search(
                query=search_query,
                limit=3
            )
            
            # Extract and format results with detailed logging
            guidance_parts = []
            for i, result in enumerate(results):
                if hasattr(result, 'text') and result.text:
                    # Limit chunk size for real-time use
                    chunk_text = result.text[:400] + "..." if len(result.text) > 400 else result.text
                    guidance_parts.append(chunk_text)
                    
                    # Log each RAG chunk being used
                    logger.info(f"📖 RAG CHUNK {i+1}: {chunk_text[:100]}...")
                    if hasattr(result, 'score'):
                        logger.info(f"   Relevance Score: {result.score:.3f}")
            
            if guidance_parts:
                logger.info(f"🎯 Using {len(guidance_parts)} MOH guideline chunks for enhancement")
                return "\n\n".join(guidance_parts)
            else:
                logger.info("⚠️ No relevant MOH guideline chunks found - using fallback")
                return self._get_basic_guidance_for_keywords(keywords)
                
        except Exception as e:
            logger.error(f"Vector DB search failed: {e}")
            return self._get_basic_guidance_for_keywords(keywords)
    
    def _get_basic_guidance_for_keywords(self, keywords: List[str]) -> str:
        """Fallback guidance when vector DB is not available"""
        guidance_map = {
            "fever": "Check temperature, assess for infection signs, consider malaria testing in endemic areas",
            "respiratory": "Assess breathing rate, listen for abnormal sounds, consider pneumonia if fever present",
            "pain": "Assess location, severity, and characteristics of pain",
            "cardiac": "Check blood pressure, pulse, consider ECG if chest pain",
            "infection": "Look for fever, elevated WBC, source of infection",
            "diabetes": "Monitor blood glucose, check for complications",
            "malaria": "Rapid diagnostic test, consider antimalarial treatment",
            "pregnancy": "Monitor blood pressure, check for danger signs",
            "pediatric": "Watch for danger signs: unable to feed, lethargy, fast breathing"
        }
        
        relevant_guidance = []
        for keyword in keywords:
            if keyword in guidance_map:
                relevant_guidance.append(f"{keyword.upper()}: {guidance_map[keyword]}")
        
        return "\n\n".join(relevant_guidance[:3]) if relevant_guidance else ""
    
    def _find_relevant_text_chunks_old(self, keyword: str) -> List[str]:
        """Find relevant text chunks containing the keyword"""
        chunks = []
        
        # Define search terms for each medical category
        search_terms = {
            "fever": ["fever", "temperature", "pyrexia", "hyperthermia", "malaria"],
            "respiratory": ["cough", "breathing", "pneumonia", "asthma", "respiratory", "lung", "chest"],
            "pain": ["pain", "ache", "discomfort", "headache", "abdominal"],
            "cardiac": ["heart", "cardiac", "chest pain", "hypertension", "blood pressure"],
            "infection": ["infection", "bacterial", "viral", "antibiotic", "sepsis"],
            "diabetes": ["diabetes", "blood sugar", "glucose", "insulin"],
            "malaria": ["malaria", "mosquito", "plasmodium", "artemether"],
            "pregnancy": ["pregnancy", "maternal", "delivery", "prenatal", "obstetric"],
            "pediatric": ["child", "infant", "pediatric", "vaccination", "growth"]
        }
        
        # Get search terms for this keyword
        terms_to_search = search_terms.get(keyword, [keyword])
        
        # Find paragraphs containing these terms
        sentences = self.guidelines_text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            
            # Check if sentence contains relevant terms
            if any(term in sentence_lower for term in terms_to_search):
                # Get surrounding context (this sentence + next one)
                sentence_index = sentences.index(sentence)
                if sentence_index < len(sentences) - 1:
                    context = sentence.strip() + ". " + sentences[sentence_index + 1].strip()
                else:
                    context = sentence.strip()
                
                # Only include substantial content (not headers or short fragments)
                if len(context) > 50 and context not in chunks:
                    chunks.append(context[:400])  # Limit chunk size
                    
                    if len(chunks) >= 2:  # Limit chunks per keyword
                        break
        
        return chunks
    
    async def enhance_prompt(self, original_prompt: str, conversation_text: str) -> str:
        """Enhance AI prompt with relevant medical guidance"""
        try:
            # Extract medical keywords
            keywords = self.extract_medical_keywords(conversation_text)
            
            if not keywords:
                return original_prompt
            
            # Get relevant guidance
            guidance = self.get_relevant_guidance(keywords)
            
            if not guidance:
                return original_prompt
            
            # Add guidance to prompt with better integration
            enhanced_prompt = original_prompt.replace(
                "If no question needed, respond: {\"content\": null, \"confidence\": 0.0}",
                f"\n\nRELEVANT MOH CLINICAL GUIDANCE:\n{guidance}\n\nConsider the above MOH guidelines when formulating questions. Ensure questions align with Rwanda healthcare protocols.\n\nIf no question needed, respond: {{\"content\": null, \"confidence\": 0.0}}"
            )
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            return original_prompt
    
    def is_available(self) -> bool:
        """Check if RAG is available"""
        return True  # Always available with fallback
    
    def is_vector_db_ready(self) -> bool:
        """Check if vector database is ready"""
        return self.vector_db_ready
    
    def get_loading_status(self) -> str:
        """Get current loading status"""
        if self.vector_db_ready:
            return "vector_db_ready"
        else:
            return "basic_fallback"

# Global instance
simple_rag = SimpleRAG()