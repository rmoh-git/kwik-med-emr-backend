#!/usr/bin/env python3
"""
Test script to validate Healthcare RAG service with source attribution.
This is critical for ensuring medical recommendations include proper sources.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

async def test_source_attribution():
    """Test the critical source attribution feature"""
    print("🏥 Testing Healthcare RAG with Source Attribution")
    print("=" * 60)
    
    try:
        # Import the healthcare RAG service
        from app.services.healthcare_rag_service import healthcare_rag_service
        
        # Test data - simulate a patient case
        patient_context = """
        PATIENT INFORMATION:
        - Name: John Doe
        - Age: 45 years old
        - Gender: Male
        - Medical Record Number: MRN123456

        CURRENT SESSION:
        - Visit Type: Follow-up
        - Chief Complaint: Persistent cough for 3 weeks
        - Practitioner: Dr. Smith
        - Session Notes: Patient reports dry cough, mild fatigue, no fever
        """
        
        session_data = """
        CONVERSATION TRANSCRIPT:
        Doctor: How long have you had this cough?
        Patient: About three weeks now. It's mostly dry, happens more at night.
        Doctor: Any fever or shortness of breath?
        Patient: No fever, but I do feel a bit tired lately.
        Doctor: Any recent travel or exposure to sick individuals?
        Patient: No recent travel, but my colleague was sick two weeks ago.
        """
        
        # Test 1: Diagnosis with Source Attribution
        print("\n📋 Test 1: Diagnosis with Source Attribution")
        print("-" * 50)
        diagnosis_result = await healthcare_rag_service.get_diagnosis_with_sources(
            patient_context, session_data
        )
        
        print(f"✅ Source Attribution Verified: {diagnosis_result.get('attribution_verified', False)}")
        print(f"📚 Source Count: {diagnosis_result.get('source_count', 0)}")
        
        if diagnosis_result.get('sources'):
            print("\n🔗 Medical Sources:")
            for i, source in enumerate(diagnosis_result['sources'][:3], 1):  # Show first 3
                print(f"  [{i}] {source.get('organization', 'Unknown')}")
                print(f"      Title: {source.get('title', 'N/A')}")
                print(f"      URL: {source.get('url', 'N/A')}")
        
        print(f"\n📄 Analysis Preview: {diagnosis_result.get('diagnosis_analysis', '')[:200]}...")
        
        # Test 2: Treatment Recommendations with Sources
        print("\n💊 Test 2: Treatment Recommendations with Sources") 
        print("-" * 50)
        treatment_result = await healthcare_rag_service.get_treatment_recommendations_with_sources(
            patient_context + "\n\nSuspected Diagnosis: Viral upper respiratory infection"
        )
        
        print(f"✅ Source Attribution Verified: {treatment_result.get('attribution_verified', False)}")
        print(f"📚 Source Count: {treatment_result.get('source_count', 0)}")
        print(f"📄 Treatment Preview: {treatment_result.get('treatment_recommendations', '')[:200]}...")
        
        # Test 3: Comprehensive Analysis
        print("\n🔍 Test 3: Comprehensive Analysis with Sources")
        print("-" * 50)
        comprehensive_result = await healthcare_rag_service.get_comprehensive_analysis_with_sources(
            patient_context + "\n" + session_data
        )
        
        print(f"✅ Source Attribution Verified: {comprehensive_result.get('attribution_verified', False)}")
        print(f"📚 Source Count: {comprehensive_result.get('source_count', 0)}")
        
        # Summary
        print("\n🎯 SOURCE ATTRIBUTION TEST SUMMARY")
        print("=" * 60)
        
        total_sources = (
            diagnosis_result.get('source_count', 0) +
            treatment_result.get('source_count', 0) + 
            comprehensive_result.get('source_count', 0)
        )
        
        all_verified = all([
            diagnosis_result.get('attribution_verified', False),
            treatment_result.get('attribution_verified', False),
            comprehensive_result.get('attribution_verified', False)
        ])
        
        print(f"📊 Total Medical Sources Attributed: {total_sources}")
        print(f"✅ All Tests Source Verified: {all_verified}")
        
        if all_verified and total_sources > 0:
            print("🎉 SUCCESS: Healthcare RAG properly attributes medical sources!")
        else:
            print("⚠️  WARNING: Source attribution may not be working correctly")
            
        return all_verified
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure all dependencies are installed: poetry install")
        return False
        
    except Exception as e:
        print(f"❌ Test Error: {e}")
        print("💡 Check your OpenAI API key and network connection")
        return False

if __name__ == "__main__":
    # Set up environment
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("💡 Add your OpenAI API key to .env file")
        sys.exit(1)
    
    # Run the test
    success = asyncio.run(test_source_attribution())
    
    if success:
        print("\n✅ Healthcare RAG with Source Attribution: READY FOR PRODUCTION")
    else:
        print("\n❌ Healthcare RAG: NEEDS DEBUGGING")
    
    sys.exit(0 if success else 1)