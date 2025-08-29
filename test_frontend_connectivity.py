#!/usr/bin/env python3
"""
Test Frontend Connectivity with Agent
Creates a simple test client to verify data flow between frontend and agent
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings

async def test_room_creation():
    """Test if we can create consultation rooms"""
    
    print("🏥 Testing Frontend → Agent Connectivity")
    print("=" * 60)
    
    # Test data
    session_id = "3586bcc4-4a1b-4ca6-9df3-96fcb0646252"
    patient_id = "4b2f7de3-966a-49ac-a10b-dfce3445d993" 
    practitioner_id = "cedb94c7-0464-4e0a-8536-db286649bbec"
    
    print(f"📋 Test Configuration:")
    print(f"   Session ID: {session_id}")
    print(f"   Patient ID: {patient_id}")
    print(f"   Practitioner ID: {practitioner_id}")
    print(f"   LiveKit URL: {settings.LIVEKIT_URL}")
    
    # Expected room name
    expected_room = f"consultation_{session_id}"
    print(f"   Expected Room: {expected_room}")
    
    print(f"\n🎯 What to Look For in Agent Logs:")
    print("-" * 50)
    print("When the agent is running, you should see:")
    print()
    print("1. 🏠 ROOM STATUS AFTER CONNECTION:")
    print(f"   Room Name: {expected_room}")
    print("   Remote Participants: 0 (initially)")
    print()
    print("2. When frontend connects:")
    print("   👤 PARTICIPANT CONNECTED: [participant_identity]")
    print("   📡 TRACK SUBSCRIBED from [participant_identity]")
    print("   🎵 Starting audio processing for [participant_identity]")
    print()
    print("3. When audio is detected:")
    print("   🎤 AUDIO FRAME #1 from [participant_identity]")
    print("   Frame size: [X] bytes")
    print("   Sample rate: [Y] Hz")
    print()
    print("4. When speech is transcribed:")
    print("   ================================================================================")
    print("   🎤 LIVE TRANSCRIPTION | PATIENT (participant_id)")  
    print("   📝 SPEECH: \"Hello doctor\"")
    print("   ⏰ TIME: 16:30:45")
    print("   ================================================================================")
    print()
    print("5. When AI generates suggestions:")
    print("   🧠 AI ANALYSIS RESULT:")
    print("   💡 SUGGESTION: [AI suggestion text]")
    print("   🚨 PRIORITY: MEDIUM")
    print("   📂 CATEGORY: QUESTIONS")
    print()
    print("6. When broadcasting to frontend:")
    print("   📡 Successfully broadcasted to [N] participants")
    
    print(f"\n🚀 To Test Complete Flow:")
    print("-" * 50)
    print("1. Start agent:")
    print("   poetry run python realtime_whisper_agent.py start")
    print()
    print("2. Start backend:")  
    print("   poetry run uvicorn app.main:app --reload")
    print()
    print("3. Use frontend to create consultation room")
    print("4. Join room with microphone enabled")
    print("5. Start talking - watch agent logs!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_room_creation())
    
    print(f"\n📊 Debugging Checklist:")
    print("=" * 50)
    print("❓ Agent not receiving participants?")
    print("   → Check if frontend is creating rooms correctly")
    print("   → Verify LiveKit credentials match")
    print() 
    print("❓ No audio frames logged?")
    print("   → Check microphone permissions in browser")
    print("   → Ensure audio is being published by frontend")
    print()
    print("❓ No transcriptions appearing?")
    print("   → Verify OpenAI API key is working") 
    print("   → Check audio quality/volume levels")
    print()
    print("❓ No AI suggestions generated?")
    print("   → Check if speech contains medical keywords")
    print("   → Verify patient context is loaded")
    
    print(f"\n✅ Enhanced Logging Now Active!")
    print("The agent will show detailed logs for all frontend interactions.")