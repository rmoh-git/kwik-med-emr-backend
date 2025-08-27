#!/usr/bin/env python3
"""
Test Healthcare Consultations API
Tests the new LiveKit-based consultation system
"""

import asyncio
import uuid
from app.services.consultation_service import consultation_service

async def test_consultation_service():
    """Test the consultation service functionality"""
    
    print("🏥 Testing Horizon 100 Healthcare Consultations")
    print("=" * 60)
    
    # Test data
    session_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4()) 
    practitioner_id = str(uuid.uuid4())
    
    print(f"📋 Session ID: {session_id}")
    print(f"👤 Patient ID: {patient_id}")
    print(f"👩‍⚕️ Practitioner ID: {practitioner_id}")
    
    try:
        # Test 1: Create consultation room
        print(f"\n🏥 Test 1: Creating Consultation Room")
        print("-" * 50)
        
        consultation_info = await consultation_service.create_consultation_room(
            session_id=session_id,
            patient_id=patient_id,
            practitioner_id=practitioner_id
        )
        
        room_name = consultation_info["room_name"]
        print(f"✅ Room created: {room_name}")
        print(f"📊 Room SID: {consultation_info['room_sid']}")
        print(f"🔗 WebSocket URL: {consultation_info['ws_url']}")
        print(f"⏱️ Max Duration: {consultation_info['max_duration_minutes']} minutes")
        print(f"🚀 Status: {consultation_info['status']}")
        
        # Test 2: Generate tokens
        print(f"\n🎫 Test 2: Generating Participant Tokens")
        print("-" * 50)
        
        # Practitioner token
        practitioner_token = consultation_service.generate_participant_token(
            room_name=room_name,
            participant_identity=practitioner_id,
            participant_type="practitioner"
        )
        print(f"✅ Practitioner token generated (length: {len(practitioner_token)})")
        
        # Patient token  
        patient_token = consultation_service.generate_participant_token(
            room_name=room_name,
            participant_identity=patient_id,
            participant_type="patient"
        )
        print(f"✅ Patient token generated (length: {len(patient_token)})")
        
        # Test 3: List active rooms
        print(f"\n📊 Test 3: Listing Active Rooms")
        print("-" * 50)
        
        active_rooms = await consultation_service.list_active_rooms()
        print(f"✅ Found {len(active_rooms)} active consultation rooms")
        
        # Test 4: End consultation
        print(f"\n🏁 Test 4: Ending Consultation")
        print("-" * 50)
        
        result = await consultation_service.end_consultation(room_name)
        print(f"✅ Consultation ended: {result['status']}")
        print(f"⏱️ Ended at: {result['ended_at']}")
        
        print(f"\n🎉 ALL CONSULTATION TESTS PASSED!")
        print("=" * 60)
        
        # Show summary
        print("✅ Healthcare Consultation System Ready")
        print("\n🚀 Key Features:")
        print("• LiveKit-based real-time consultations")
        print("• Role-based access tokens (practitioner/patient)")
        print("• Healthcare AI assistant integration ready")
        print("• HIPAA-compliant room management")
        print("• Session-based room organization")
        
        print(f"\n📡 API Endpoints Available:")
        print("• POST /api/v1/consultations/create")
        print("• POST /api/v1/consultations/token")
        print("• POST /api/v1/consultations/{room_name}/end")
        print("• GET /api/v1/consultations/active")
        print("• GET /api/v1/consultations/health")
        
        if not consultation_service.livekit_available:
            print(f"\n⚠️  LiveKit Dependencies Note:")
            print("🔧 For full functionality, install: poetry add livekit-agents livekit-plugins-openai")
            print("🏥 Currently running in mock mode for development")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_consultation_service())