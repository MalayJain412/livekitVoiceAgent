import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio
from typing import Optional, Tuple
import re
import time
load_dotenv()  # Load environment variables early

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero
from prompts import set_agent_instruction
from persona_handler import load_persona_from_dialed_number as load_persona_from_api
from mobile_api import get_campaign_metadata_for_call
from tools import (
    create_lead, 
    detect_lead_intent, 
    HangupTool
)
import config
from instances import get_instances_from_payload
from session_manager import SessionManager
from validation import validate_agent_availability, hangup_call

try:
    from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput
except ImportError:
    logging.critical("Could not import LiveKitAPI. Please run: pip install livekit-api")

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)


# --------------------------------------------
# STRICT MODE: Extract number only from room name
# --------------------------------------------
def extract_number_from_room_name(room_name: str) -> Optional[str]:
    """Extracts the dialed number from room name like 'number-_918655048643'."""
    match = re.search(r'number-[_+]?(\d+)', room_name)
    if match:
        return '+' + match.group(1)
    return None


async def get_sip_participant_and_number(ctx: JobContext) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract SIP participant and dialed number strictly from room name.
    No metadata, no fallbacks, no defaults.
    """
    try:
        room_name = ctx.room.name
        logging.info(f"Extracting dialed number from room name: {room_name}")

        dialed_number = extract_number_from_room_name(room_name)
        if not dialed_number:
            logging.warning(f"Could not extract dialed number from room name: {room_name}")
            return None, None

        logging.info(f"Successfully extracted dialed number from room name: {dialed_number}")

        # Find SIP participant identity (if exists)
        participant_identity = None
        if hasattr(ctx.room, "participants") and ctx.room.participants:
            for p in ctx.room.participants.values():
                if p.identity.startswith("sip_"):
                    participant_identity = p.identity
                    break

        return participant_identity, dialed_number

    except Exception as e:
        logging.error(f"Error extracting number from room name: {e}")
        return None, None

async def load_persona_from_dialed_number(dialed_number: str):
    """Load persona configuration from CRM API using dialed number."""
    return await load_persona_from_api(dialed_number)

def apply_persona_to_agent(agent: Agent, persona_config: dict):
    """Apply persona configuration to the agent."""
    # This function can be used if needed to modify agent after creation
    pass

def attach_persona_to_session(session: AgentSession, full_config: dict, persona_name: str, session_instructions: str, closing_message: str):
    """Attach persona configuration to the session for later use."""
    session.persona_config = full_config
    session.persona_name = persona_name
    session.session_instructions = session_instructions
    session.closing_message = closing_message

class Assistant(Agent):
    def __init__(self, custom_instructions=None, end_call_tool=None):
        # Require custom_instructions from API - no fallback to defaults
        if not custom_instructions:
            raise ValueError("Agent requires custom_instructions from API - no default fallbacks allowed")

        super().__init__(
            instructions=custom_instructions,
            tools=[
                # get_weather, 
                # search_web, 
                # triotech_info, 
                create_lead, 
                detect_lead_intent, 
                end_call_tool],
        )


async def entrypoint(ctx: JobContext):
    # Setup conversation logging
    config.setup_conversation_log()
    
    # -----------------------------------------------------------------
    # --- RECORDING (Egress) BLOCK ---
    # -----------------------------------------------------------------
    lkapi = None
    try:
        logging.info(f"Starting recording for room: {ctx.room.name}")

        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        if not (livekit_url and livekit_api_key and livekit_api_secret):
            logging.error("Recording skipped: LIVEKIT_URL / API_KEY / API_SECRET not all set")
        else:
            # Ensure HTTP host
            http_host = livekit_url
            if http_host.startswith("ws://"):
                http_host = "http://" + http_host[len("ws://"):]
            elif http_host.startswith("wss://"):
                http_host = "https://" + http_host[len("wss://"):]

            logging.info(f"Recording: LiveKit API host = {http_host}")

            lkapi = LiveKitAPI(http_host, livekit_api_key, livekit_api_secret)

            filename = f"recordings/{ctx.room.name}-{int(time.time())}.mp4"

            file_output = EncodedFileOutput(
                filepath=filename
                # Optionally: azure=AzureBlobUpload(...), s3=..., gcp=...
            )

            req = RoomCompositeEgressRequest(
                room_name=ctx.room.name,
                audio_only=True,
                file_outputs=[file_output]
            )

            info = await lkapi.egress.start_room_composite_egress(req)
            logging.info(f"Recording started: egress_id={info.egress_id}, file={filename}")

    except Exception as e:
        logging.error(f"Recording error for room {ctx.room.name}: {e}")
    finally:
        if lkapi:
            await lkapi.aclose()
    # -----------------------------------------------------------------
    # --- END OF RECORDING BLOCK ---
    # -----------------------------------------------------------------

    
    # Extract dialed number from SIP participant in the room
    participant_identity, dialed_number = await get_sip_participant_and_number(ctx)
    
    if not dialed_number:
        logging.warning("Could not extract dialed number from room participants")
        # Create minimal session for error message
        instances = get_instances_from_payload(None)
        session = AgentSession(
            stt=instances["stt"],
            llm=instances["llm"], 
            tts=instances["tts"],
            vad=instances["vad"],
        )
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
        
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )
        
        await session.say("Sorry, we could not identify your call. Please try again.")
        await hangup_call()
        return
    
    logging.info(f"Extracted dialed number: {dialed_number}")
    
    # Load persona configuration from dialed number
    try:
        agent_instructions, session_instructions, closing_message, persona_name, full_config = await load_persona_from_dialed_number(dialed_number)
        logging.info(f"Successfully loaded persona for dialed number {dialed_number}: {persona_name}")
        
        # Get campaign metadata for file naming and matching
        from transcript_logger import set_current_session_id, get_current_session_id, set_dialed_number
        session_id = get_current_session_id() or f"session_{int(time.time())}"
        set_current_session_id(session_id)
        set_dialed_number(dialed_number)
        
        campaign_metadata = get_campaign_metadata_for_call(dialed_number, session_id)
        
        logging.info(f"Campaign metadata collected: {campaign_metadata}")
        logging.info(f"Session ID: {session_id}, Dialed Number: {dialed_number}")
        
    except ValueError as e:
        logging.warning(f"Persona validation failed for {dialed_number}: {e}")
        # Create minimal session for error message
        instances = get_instances_from_payload(None)
        session = AgentSession(
            stt=instances["stt"],
            llm=instances["llm"], 
            tts=instances["tts"],
            vad=instances["vad"],
        )
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
        
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )
        
        await session.say("Sorry, this number is not configured for service. Please contact support.")
        await hangup_call()
        return
    except Exception as e:
        logging.error(f"Error loading persona for {dialed_number}: {e}")
        # Create minimal session for error message
        instances = get_instances_from_payload(None)
        session = AgentSession(
            stt=instances["stt"],
            llm=instances["llm"], 
            tts=instances["tts"],
            vad=instances["vad"],
        )
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
        
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )
        
        await session.say("Sorry, there was an error loading the service configuration. Please try again later.")
        await hangup_call()
        return
    
    # VALIDATION: Check agent availability
    is_available, failure_reason = validate_agent_availability(full_config)
    if not is_available:
        logging.warning(f"Agent validation failed: {failure_reason}")
        
        # Create minimal session for apology message
        instances = get_instances_from_payload(None)
        session = AgentSession(
            stt=instances["stt"],
            llm=instances["llm"], 
            tts=instances["tts"],
            vad=instances["vad"],
        )
        
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
        
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )
        
        await session.say("Sorry, currently the agent is not available. Please try later.")
        await hangup_call()
        return
    
    # Create the hangup event and tool
    hangup_event = asyncio.Event()
    hangup_tool = HangupTool(hangup_event=hangup_event)

    # Create agent with persona instructions
    agent = Assistant(custom_instructions=agent_instructions, end_call_tool=hangup_tool.end_call)
    logging.info(f"Created agent with persona instructions for: {persona_name}")

    # Get AI service instances
    instances = get_instances_from_payload(full_config)
    
    session = AgentSession(
        stt=instances["stt"],
        llm=instances["llm"],
        tts=instances["tts"],
        vad=instances["vad"],
    )

    # Attach persona configuration to session
    attach_persona_to_session(session, full_config, persona_name, session_instructions, closing_message)
    
    # Initialize session manager
    session_manager = SessionManager(session)
    
    # Set campaign metadata in session manager for file naming
    session_manager.set_campaign_metadata(campaign_metadata)
    
    logging.info("SessionManager created successfully with campaign metadata")
    
    # Setup session logging and monitoring
    await session_manager.setup_session_logging()
    await session_manager.setup_shutdown_callback()
    logging.info("SessionManager setup completed")

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
        room_output_options=RoomOutputOptions(audio_enabled=True),
    )

    # Log persona application event
    session_manager.log_persona_applied_event(persona_name, full_config, session_instructions, closing_message)
    
    # Start background history watcher AFTER session starts
    await session_manager.start_history_watcher()
    logging.info("SessionManager history watcher started")

    # Generate initial reply with persona-aware instructions
    if not session_instructions:
        raise ValueError(f"Session instructions required from API for persona {persona_name} - no defaults allowed")

    # Use persona's conversation structure for session behavior
    initial_instruction = session_instructions
    logging.info(f"Using persona session instructions for: {persona_name}")
    
    logging.info("Agent is running, waiting for user input or hangup signal...")
    
    # Generate the initial reply to start the conversation
    await session.generate_reply(instructions=initial_instruction)
    
    # Wait for the hangup signal
    await hangup_event.wait()
    
    logging.info("Hangup signal received.")

    # --- HANGUP SEQUENCE ---
    # Play the pre-defined closing message from the persona config
    if closing_message:
        logging.info(f"Playing closing message: {closing_message}")
        await session.say(closing_message)
        # Add a small delay to ensure message finishes playing before hangup
        await asyncio.sleep(2)
    
    await hangup_call()
    logging.info("Call has been successfully terminated.")

    logging.info("Agent entrypoint finished.")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="friday-assistant"
        )
    )