"""
Healthcare Voice Agent for Horizon 100
A simple LiveKit agent for healthcare consultations with real-time transcription
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

try:
    from livekit import rtc, api
    from livekit.agents import (
        AutoSubscribe,
        JobContext,
        JobProcess,
        WorkerOptions,
        cli,
        llm,
    )
    from livekit.agents.multimodal import MultimodalAgent
    from livekit.plugins import openai, silero
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    print("LiveKit agents not available. Install with: poetry add livekit-agents livekit-plugins-openai livekit-plugins-silero")

from app.core.config import settings

load_dotenv()
logger = logging.getLogger("healthcare-agent")
logger.setLevel(logging.INFO)

def prewarm(proc: JobProcess):
    """Prewarm the agent with VAD model"""
    if LIVEKIT_AVAILABLE:
        proc.userdata["vad"] = silero.VAD.load()

def extract_session_info(room_name: str) -> dict:
    """Extract session information from room name"""
    # Format: consultation_<session_id> or similar
    if room_name.startswith("consultation_"):
        session_id = room_name.replace("consultation_", "")
        return {
            'session_id': session_id,
            'consultation_type': 'healthcare',
            'room_name': room_name
        }
    else:
        return {
            'session_id': room_name,
            'consultation_type': 'general',
            'room_name': room_name
        }

async def entrypoint(ctx: JobContext):
    """Main agent entrypoint for healthcare consultations"""
    
    if not LIVEKIT_AVAILABLE:
        logger.error("LiveKit agents not available. Cannot start healthcare agent.")
        return
    
    # Extract session information
    session_info = extract_session_info(ctx.room.name)
    logger.info(f"Starting healthcare consultation for room: {ctx.room.name}")
    logger.info(f"Session info: {session_info}")
    
    # Healthcare-specific system instructions
    system_instructions = (
        "You are a healthcare AI assistant for the Horizon 1000 platform. "
        "You assist during medical consultations by providing real-time support to healthcare practitioners. "
        
        "Your capabilities include:"
        "- Helping with medical terminology and definitions"
        "- Providing clinical decision support based on established medical guidelines"
        "- Assisting with documentation and note-taking during consultations"
        "- Offering reminders about standard protocols and procedures"
        
        "Important guidelines:"
        "- You are an assistant to healthcare professionals, not a replacement"
        "- Always defer to the practitioner's clinical judgment" 
        "- Do not provide direct medical advice to patients"
        "- Maintain patient confidentiality and HIPAA compliance"
        "- Keep responses concise and professional"
        "- If asked about specific diagnoses or treatments, remind that these decisions must be made by qualified practitioners"
        
        "During consultations:"
        "- Listen for key medical terms and offer clarifications when appropriate"
        "- Help with accurate medical documentation"
        "- Suggest relevant follow-up questions the practitioner might consider"
        "- Provide evidence-based information when requested"
        
        "Remember: You are here to support the healthcare team, not to make medical decisions."
    )
    
    # Connect to the room
    logger.info(f"Connecting to healthcare consultation room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Wait for participants (practitioner and patient)
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant {participant.identity} joined healthcare consultation")
    
    # Start the healthcare consultation assistant
    await run_healthcare_agent(ctx, participant, system_instructions, session_info)
    
    logger.info("Healthcare agent started successfully")

async def run_healthcare_agent(ctx: JobContext, participant: rtc.Participant, instructions: str, session_info: dict):
    """Run the healthcare multimodal agent"""
    logger.info("Starting healthcare multimodal agent")
    
    # Create the OpenAI realtime model
    model = openai.realtime.RealtimeModel(
        instructions=instructions,
        modalities=["audio", "text"],
        # Use a model suitable for healthcare applications
        # Note: Ensure you have proper API access for medical use cases
    )
    
    # Create the multimodal agent
    assistant = MultimodalAgent(model=model)
    
    # Set up event listeners for healthcare-specific logging
    @assistant.on("user_speech_committed")
    def _on_user_speech_committed(transcript: str):
        logger.info(f"[{session_info['session_id']}] User: {transcript}")
        # Here you could integrate with your healthcare logging system
        # log_healthcare_interaction(session_info, "user", transcript)

    @assistant.on("agent_speech_committed") 
    def _on_agent_speech_committed(transcript: str):
        logger.info(f"[{session_info['session_id']}] Assistant: {transcript}")
        # Here you could integrate with your healthcare logging system
        # log_healthcare_interaction(session_info, "assistant", transcript)
    
    # Start the assistant
    assistant.start(ctx.room, participant)
    
    # Get the first session and provide an initial greeting
    session = model.sessions[0]
    session.conversation.item.create(
        llm.ChatMessage(
            role="user",
            content="Please introduce yourself as the Horizon 1000 healthcare AI assistant and ask how you can help during this consultation.",
        )
    )
    session.response.create()

def main():
    """Main function to run the healthcare agent"""
    
    if not LIVEKIT_AVAILABLE:
        print("❌ LiveKit agents not available.")
        print("📦 Install with: poetry add livekit-agents livekit-plugins-openai livekit-plugins-silero")
        return
    
    # Validate required settings
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        print("❌ LiveKit credentials not configured.")
        print("🔧 Set LIVEKIT_API_KEY and LIVEKIT_API_SECRET in your .env file")
        return
        
    if not settings.OPENAI_API_KEY:
        print("❌ OpenAI API key not configured.")
        print("🔧 Set OPENAI_API_KEY in your .env file")
        return
    
    print("🏥 Starting Horizon 100 Healthcare Agent")
    print(f"🔗 LiveKit URL: {settings.LIVEKIT_URL}")
    print(f"🤖 OpenAI Model: {settings.OPENAI_MODEL}")
    
    # Configure worker options
    options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        ws_url=settings.LIVEKIT_URL
    )
    
    # Run the agent
    cli.run_app(options)

if __name__ == "__main__":
    main()