#!/usr/bin/env python3
"""
One-time RAG setup script
Processes MOH guidelines PDF and creates vector embeddings
Run this once to set up the vector database for the whisper agent
"""
import logging
import asyncio
from pathlib import Path
import sys

# Add project to path
sys.path.append(str(Path(__file__).parent))

from simple_rag import SimpleRAG

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_embeddings_from_pdf(pdf_path: Path) -> dict:
    """Process PDF and create vector embeddings directly"""
    try:
        # Extract text from PDF
        logger.info("📄 Extracting text from PDF...")
        text_content = extract_pdf_text(pdf_path)
        
        if not text_content or len(text_content) < 1000:
            logger.error("❌ PDF extraction failed or returned minimal content")
            return {"success": False, "error": "PDF extraction failed"}
        
        logger.info(f"✅ Extracted {len(text_content)} characters from PDF")
        
        # Split into chunks
        chunks = create_text_chunks(text_content)
        logger.info(f"📊 Created {len(chunks)} text chunks")
        
        # Use agno knowledge base approach for proper document insertion
        logger.info("🔧 Using agno knowledge base for PDF processing...")
        
        try:
            from agno.embedder.openai import OpenAIEmbedder
            from agno.vectordb.lancedb import LanceDb
            from agno.knowledge.text import TextKnowledgeBase
            import os
            
            # Get OpenAI API key
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                try:
                    from app.core.config import settings
                    openai_key = settings.OPENAI_API_KEY
                except ImportError:
                    pass
            
            if not openai_key:
                logger.error("❌ OpenAI API key not found")
                return {"success": False, "error": "OpenAI API key not found"}
            
            # Initialize embedder and vector database
            embedder = OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=openai_key
            )
            
            vector_db = LanceDb(
                table_name="moh_guidelines_chunks",
                embedder=embedder
            )
            
            # Create knowledge base from text content
            logger.info("🚀 Creating knowledge base from PDF text...")
            
            # Write text to temporary file for TextKnowledgeBase
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(text_content)
                temp_file_path = temp_file.name
            
            knowledge = TextKnowledgeBase(
                path=temp_file_path,
                vector_db=vector_db,
                chunk=True,  # Enable automatic chunking
                chunk_size=500,
                chunk_overlap=100
            )
            
            # Load the knowledge into vector database
            knowledge.load()
            
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)
            
            logger.info(f"✅ Successfully loaded PDF content into knowledge base")
            
            return {
                "success": True,
                "total_chunks": len(chunks),
                "total_characters": len(text_content),
                "vector_table": "moh_guidelines_chunks"
            }
            
        except Exception as e:
            logger.error(f"❌ Vector database error: {e}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"❌ PDF processing error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using available libraries"""
    # Try pdfplumber first (more robust)
    if PDFPLUMBER_AVAILABLE:
        text_content = extract_with_pdfplumber(pdf_path)
        if text_content and len(text_content) > 1000:
            return text_content
    
    # Fallback to pypdf
    if PYPDF_AVAILABLE:
        text_content = extract_with_pypdf(pdf_path)
        if text_content and len(text_content) > 1000:
            return text_content
    
    raise Exception("No suitable PDF library available or PDF extraction failed")

def extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber"""
    try:
        text_content = ""
        pages_processed = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} total pages (using pdfplumber)")
            
            # Extract text from first pages (for POC, limit to manageable size)
            max_pages = min(20, len(pdf.pages))  # Process up to 20 pages for POC setup
            
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
        
        logger.info(f"✅ pdfplumber extracted {len(text_content)} characters from {pages_processed}/{max_pages} pages")
        return text_content
        
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return ""

def extract_with_pypdf(pdf_path: Path) -> str:
    """Extract text using pypdf (fallback)"""
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
        
        logger.info(f"✅ pypdf extracted {len(text_content)} characters from {pages_processed}/{max_pages} pages")
        return text_content
        
    except Exception as e:
        logger.error(f"pypdf extraction failed: {e}")
        return ""

def create_text_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Split text into overlapping chunks for better retrieval"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        # Only add substantial chunks
        if len(chunk_text.strip()) > 100:
            chunks.append(chunk_text.strip())
    
    return chunks

async def setup_vector_database():
    """One-time setup: Process PDF and create vector database"""
    try:
        logger.info("🚀 Starting RAG setup...")
        
        # Check if PDF exists
        pdf_path = Path(__file__).parent / "data" / "guidelines" / "moh_guidelines.pdf"
        if not pdf_path.exists():
            logger.error(f"❌ MOH guidelines PDF not found at: {pdf_path}")
            logger.error("Please place your PDF file there first")
            return False
        
        logger.info(f"📄 Found PDF: {pdf_path} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Process PDF and create embeddings
        logger.info("🔄 Processing PDF and creating embeddings...")
        result = await create_embeddings_from_pdf(pdf_path)
        
        if result["success"]:
            logger.info("✅ RAG setup completed successfully!")
            logger.info(f"📊 Processed {result['total_chunks']} chunks")
            logger.info(f"📊 Total characters: {result['total_characters']}")
            logger.info(f"🗄️  Vector table: {result['vector_table']}")
            return True
        else:
            logger.error(f"❌ RAG setup failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_search():
    """Test that vector search is working"""
    try:
        logger.info("🧪 Testing vector search...")
        
        rag = SimpleRAG()
        if not rag.is_vector_db_ready():
            logger.warning("⚠️ Vector DB not ready - test skipped")
            return
        
        # Test search
        keywords = ["fever", "malaria"]
        guidance = rag.get_relevant_guidance(keywords)
        
        if guidance:
            logger.info("✅ Vector search test passed!")
            logger.info(f"📋 Sample guidance (first 200 chars): {guidance[:200]}...")
        else:
            logger.warning("⚠️ Vector search returned no results")
            
    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")

if __name__ == "__main__":
    print("🏥 MOH Guidelines RAG Setup")
    print("=" * 40)
    
    # Run setup
    success = asyncio.run(setup_vector_database())
    
    if success:
        print("\n" + "=" * 40)
        print("✅ Setup completed successfully!")
        print("🚀 Your whisper agent is now ready with MOH guidelines")
        print("\nTo start the agent:")
        print("poetry run python realtime_whisper_agent.py dev")
        
        # Test the setup
        print("\n🧪 Testing vector search...")
        test_vector_search()
        
    else:
        print("\n" + "=" * 40)
        print("❌ Setup failed!")
        print("Please check the error messages above and try again")
        sys.exit(1)