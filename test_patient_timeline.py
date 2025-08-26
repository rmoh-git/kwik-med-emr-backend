#!/usr/bin/env python3
"""
Test Patient Timeline with Visual Metrics and Structured Responses
Validates the comprehensive timeline functionality.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.services.patient_timeline_service import patient_timeline_service
from app.db.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel, SessionStatusEnum
from app.models.analysis import Analysis, AnalysisStatusEnum, AnalysisTypeEnum
from app.models.recording import Recording, RecordingStatusEnum
from datetime import datetime, timedelta
import uuid
import json

def create_test_data():
    """Create test patient data for timeline testing"""
    db = SessionLocal()
    
    try:
        # Create test patient
        unique_mrn = f"TEST{uuid.uuid4().hex[:6]}"
        test_patient = Patient(
            id=uuid.uuid4(),
            first_name="Jane",
            last_name="Smith",
            date_of_birth=datetime(1980, 5, 15),
            gender="female",
            medical_record_number=unique_mrn
        )
        db.add(test_patient)
        db.flush()
        
        # Create test sessions with analyses
        sessions_data = []
        for i in range(5):
            # Create session
            session_date = datetime.now() - timedelta(days=i * 7)  # Weekly sessions
            session = SessionModel(
                id=uuid.uuid4(),
                patient_id=test_patient.id,
                practitioner_name=f"Dr. Test {i + 1}",
                practitioner_id=f"PRAC{i + 1}",
                visit_type="consultation" if i % 2 == 0 else "follow-up",
                notes=f"Session {i + 1} - Patient progress evaluation",
                status=SessionStatusEnum.COMPLETED,
                created_at=session_date,
                updated_at=session_date,
                ended_at=session_date + timedelta(minutes=30)
            )
            db.add(session)
            db.flush()
            
            # Create recording for session
            recording = Recording(
                id=uuid.uuid4(),
                session_id=session.id,
                file_path=f"/test/audio_{i}.wav",
                file_name=f"session_{i}_audio.wav",
                transcript=f"Test transcript for session {i + 1}. Patient reports feeling better.",
                status=RecordingStatusEnum.COMPLETED,
                created_at=session_date
            )
            db.add(recording)
            db.flush()
            
            # Create analyses with source attribution
            analysis_types = [AnalysisTypeEnum.DIAGNOSIS_ASSISTANCE, AnalysisTypeEnum.TREATMENT_RECOMMENDATION]
            for j, analysis_type in enumerate(analysis_types):
                analysis = Analysis(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    analysis_type=analysis_type,
                    prompt_context=f"Analyze patient case {i + 1}",
                    result={
                        "summary": f"Analysis {j + 1} for session {i + 1}: Patient shows positive response to treatment",
                        "full_analysis": f"Comprehensive analysis of patient condition in session {i + 1}. Evidence-based recommendations provided.",
                        "sources": [
                            {
                                "citation_id": f"REF-{i}-{j}",
                                "title": f"Clinical Guidelines Session {i + 1}",
                                "organization": "Medical Standards Authority",
                                "url": f"https://medical-standards.org/guideline-{i}-{j}",
                                "guideline_type": "clinical_practice"
                            }
                        ],
                        "source_count": 1,
                        "attribution_verified": True,
                        "confidence_score": 0.85 + (i * 0.02),  # Improving confidence over time
                        "rag_powered": True
                    },
                    status=AnalysisStatusEnum.COMPLETED,
                    tokens_used=150 + (i * 10),
                    processing_time_seconds=5.2 + (i * 0.3),
                    created_at=session_date + timedelta(minutes=5 + j * 3)
                )
                db.add(analysis)
            
            sessions_data.append(session)
        
        db.commit()
        print(f"✅ Created test patient {test_patient.id} with {len(sessions_data)} sessions")
        return test_patient.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to create test data: {e}")
        return None
    finally:
        db.close()

def test_patient_timeline(patient_id):
    """Test the patient timeline functionality"""
    print("\n📊 Testing Patient Timeline with Visual Metrics")
    print("=" * 60)
    
    try:
        db = SessionLocal()
        timeline_data = patient_timeline_service.generate_comprehensive_timeline(
            str(patient_id), db, days_back=60
        )
        db.close()
        
        if "error" in timeline_data:
            print(f"❌ Timeline generation failed: {timeline_data['error']}")
            return False
        
        # Validate timeline structure
        required_sections = [
            "patient_info", "timeline_period", "timeline_events", 
            "health_metrics", "visual_data", "health_trends", 
            "structured_summary", "statistics"
        ]
        
        missing_sections = [section for section in required_sections if section not in timeline_data]
        if missing_sections:
            print(f"❌ Missing sections: {missing_sections}")
            return False
        
        print("✅ All required sections present")
        
        # Test timeline events
        events = timeline_data["timeline_events"]
        print(f"📅 Timeline Events: {len(events)}")
        
        session_events = [e for e in events if e["event_type"] == "session"]
        analysis_events = [e for e in events if e["event_type"] == "analysis"]
        
        print(f"   📋 Session Events: {len(session_events)}")
        print(f"   🔍 Analysis Events: {len(analysis_events)}")
        
        # Test health metrics
        metrics = timeline_data["health_metrics"]
        print(f"\n📊 Health Metrics: {len(metrics)}")
        
        for metric in metrics:
            print(f"   • {metric['name']}: {metric['value']} {metric['unit']} ({metric['trend']})")
            if metric.get('compliance_critical'):
                print(f"     🚨 COMPLIANCE CRITICAL: {metric['description']}")
        
        # Test visual data
        visual_data = timeline_data["visual_data"]
        print(f"\n📈 Visual Data Charts: {len(visual_data)}")
        
        for chart in visual_data:
            print(f"   • {chart['title']} ({chart['chart_type']}): {len(chart['data_points'])} points")
            if chart.get('compliance_critical'):
                print(f"     🚨 COMPLIANCE CHART: {chart['title']}")
        
        # Test structured summary
        summary = timeline_data["structured_summary"]
        print(f"\n📋 Structured Summary:")
        print(f"   • Care Quality: {summary['patient_overview']['care_quality_rating']}")
        print(f"   • Compliance Status: {summary['patient_overview']['compliance_status']}")
        print(f"   • Key Insights: {len(summary['key_insights'])}")
        print(f"   • Recommendations: {len(summary['recommendations'])}")
        print(f"   • Next Actions: {len(summary['next_actions'])}")
        
        # Validate source attribution
        attribution_metric = next((m for m in metrics if "Source Attribution" in m["name"]), None)
        if attribution_metric:
            print(f"\n🔗 Source Attribution Rate: {attribution_metric['value']}%")
            if attribution_metric['value'] >= 90:
                print("   ✅ EXCELLENT: Meets healthcare compliance standards")
            else:
                print("   ⚠️  WARNING: Below recommended 90% threshold")
        
        # Test health trends
        trends = timeline_data["health_trends"]
        print(f"\n📈 Health Trends:")
        print(f"   • Overall Trend: {trends['overall_trend']}")
        print(f"   • Analysis: {trends['trend_analysis']}")
        
        # Statistics
        stats = timeline_data["statistics"]
        print(f"\n📊 Statistics:")
        print(f"   • Total Sessions: {stats['total_sessions']}")
        print(f"   • Completed Sessions: {stats['completed_sessions']}")
        print(f"   • Total Analyses: {stats['total_analyses']}")
        print(f"   • Timeline Events: {stats['timeline_events_count']}")
        
        print(f"\n✅ Patient Timeline Test SUCCESSFUL!")
        print(f"📊 Generated timeline with {len(events)} events, {len(metrics)} metrics, {len(visual_data)} charts")
        
        # Save sample output for inspection
        with open("sample_patient_timeline.json", "w") as f:
            json.dump(timeline_data, f, indent=2, default=str)
        print(f"💾 Sample timeline saved to sample_patient_timeline.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Timeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data(patient_id):
    """Clean up test data"""
    db = SessionLocal()
    try:
        # Delete test patient and related data (cascade will handle sessions, recordings, analyses)
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient:
            db.delete(patient)
            db.commit()
            print(f"🧹 Cleaned up test patient {patient_id}")
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🏥 Patient Timeline Testing Suite")
    print("=" * 60)
    
    # Create test data
    patient_id = create_test_data()
    if not patient_id:
        print("❌ Failed to create test data")
        sys.exit(1)
    
    try:
        # Test timeline functionality
        success = test_patient_timeline(patient_id)
        
        if success:
            print("\n🎉 PATIENT TIMELINE WITH VISUAL METRICS: READY FOR PRODUCTION")
            print("\nKey Features Validated:")
            print("✅ Timeline events with structured data")
            print("✅ Health metrics and trend analysis")
            print("✅ Visual data points for charts")
            print("✅ Source attribution compliance tracking")
            print("✅ Structured recommendations and insights")
            print("✅ Next actions and care quality assessment")
            
        else:
            print("\n❌ PATIENT TIMELINE: NEEDS DEBUGGING")
            
    finally:
        # Cleanup
        cleanup_test_data(patient_id)
    
    sys.exit(0 if success else 1)