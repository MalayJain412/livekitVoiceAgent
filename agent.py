"""
LiveKit Agent (cagent.py)
This script runs a LiveKit agent worker ("friday-assistant") that handles
incoming SIP calls. It performs the following steps:
1.  Connects to the LiveKit room.
2.  Starts an Egress (audio recording) for the call.
3.  Identifies the dialed number from SIP information.
4.  Loads a dynamic "persona" (config, prompts, voice) from an external API.
5.  Validates agent availability (e.g., business hours).
6.  Runs the AI conversation using STT, LLM, and TTS.
7.  Listens for a hangup signal (from a tool or user phrase) to end the call.
"""

import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio
import time
from typing import Optional, Tuple

# --- MODIFIED FILE LOADING ---
# Explicitly find and load the .env file from the script's directory
try:
    # Get the absolute path of the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
except NameError:
    # Fallback if __file__ is not defined (e.g., in a REPL)
    script_dir = os.getcwd()
    env_path = os.path.join(script_dir, '.env')
    print(f"--- WARNING: __file__ not defined, falling back to CWD: {script_dir} ---")

if os.path.exists(env_path):
    print(f"--- Loading .env file from: {env_path} ---")
    load_dotenv(dotenv_path=env_path)
else:
    print(f"--- WARNING: .env file not found at {env_path} ---")
    load_dotenv() # Try default behavior (searches CWD and parent dirs)


from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero
from prompts import set_agent_instruction
from persona_handler import load_persona_from_dialed_number as load_persona_from_api
from tools import (
    # get_weather,
    # search_web,
    # triotech_info,
    create_lead,
    detect_lead_intent,
    HangupTool
)
import config
from instances import get_instances_from_payload
from session_manager import SessionManager
from validation import validate_agent_availability, hangup_call

# --- CORRECTED IMPORTS ---
try:
    from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput
except ImportError:
    logging.critical("Could not import LiveKitAPI. Please run: pip install livekit-api")
# --- END OF CORRECTED IMPORTS ---

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

async def get_sip_participant_and_number(ctx: JobContext) -> Tuple[Optional[str], Optional[str]]:
    """Extract SIP participant and dialed number from the room. 
    STRICT MODE: Only returns proper dialed numbers, never falls back to caller numbers or defaults."""
    try:
        room_name = ctx.room.name
        logging.info(f"Processing room: {room_name}")
        
        # Method 1: Extract dialed number from room name routing patterns
        if "_to_" in room_name:
            # Extract number after "_to_" (this should be the dialed number)
            to_start = room_name.find("_to_") + 4
            to_end = room_name.find("_", to_start)
            if to_end == -1:
                to_end = len(room_name)
            
            dialed_part = room_name[to_start:to_end]
            dialed_number = _extract_number_from_sip_uri(dialed_part)
            if dialed_number:
                logging.info(f"Successfully extracted dialed number from room name routing: {dialed_number}")
                participant_identity = await _get_sip_participant_identity(ctx)
                return participant_identity or "sip_unknown", dialed_number
        
        # Method 2: Check SIP participant attributes for dialed number
        if hasattr(ctx.room, 'participants') and ctx.room.participants:
            for participant in ctx.room.participants.values():
                if participant.identity.startswith("sip_"):
                    if hasattr(participant, 'attributes') and participant.attributes:
                        # Look for SIP-specific attributes that contain the dialed number
                        dialed_to = (participant.attributes.get("lk_sip_to") or 
                                   participant.attributes.get("sip_to") or 
                                   participant.attributes.get("to_number") or
                                   participant.attributes.get("dialed_number") or
                                   participant.attributes.get("destination_number"))
                        if dialed_to:
                            dialed_number = _extract_number_from_sip_uri(dialed_to)
                            if dialed_number:
                                logging.info(f"Successfully extracted dialed number from participant attributes: {dialed_number}")
                                return participant.identity, dialed_number
        
        # Method 3: Check room metadata for SIP routing information  
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            dialed_to = (ctx.room.metadata.get('sip_to') or 
                        ctx.room.metadata.get('to') or 
                        ctx.room.metadata.get('dialed_number') or
                        ctx.room.metadata.get('destination') or
                        ctx.room.metadata.get('destination_number'))
            if dialed_to:
                dialed_number = _extract_number_from_sip_uri(dialed_to)
                if dialed_number:
                    logging.info(f"Successfully extracted dialed number from room metadata: {dialed_number}")
                    participant_identity = await _get_sip_participant_identity(ctx)
                    return participant_identity or "sip_unknown", dialed_number

        # STRICT MODE: No fallbacks to caller numbers or defaults
        logging.error(f"FAILED to extract dialed number from room {room_name}. No fallbacks will be used.")
        logging.error("Available data for debugging:")
        if hasattr(ctx.room, 'participants') and ctx.room.participants:
            for participant in ctx.room.participants.values():
                logging.error(f"  Participant: {participant.identity}")
                if hasattr(participant, 'attributes') and participant.attributes:
                    logging.error(f"    Attributes: {participant.attributes}")
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            logging.error(f"  Room metadata: {ctx.room.metadata}")
        
        return None, None
    except Exception as e:
        logging.error(f"Error extracting SIP participant and number: {e}")
        return None, None


async def _get_sip_participant_identity(ctx: JobContext) -> Optional[str]:
    """Helper function to get SIP participant identity."""
    try:
        if hasattr(ctx.room, 'participants') and ctx.room.participants:
            for participant in ctx.room.participants.values():
                if participant.identity.startswith("sip_"):
                    return participant.identity
        return None
    except Exception as e:
        logging.error(f"Error getting SIP participant identity: {e}")
        return None

def _extract_number_from_sip_uri(uri: str) -> Optional[str]:
    """Extract phone number from SIP URI format or participant identity."""
    try:
        # Handle participant identity format: sip_+1234567890
        if uri.startswith("sip_"):
            # Remove sip_ prefix
            uri = uri[4:]

            # Remove + if present
            if uri.startswith("+"):
                uri = uri[1:]

            # Should be digits only
            if uri.isdigit():
                return uri

        # Handle sip:+1234567890@domain format
        if uri.startswith("sip:"):
            # Remove sip: prefix
            uri = uri[4:]

            # Remove @domain part
            if "@" in uri:
                uri = uri.split("@")[0]

            # Remove + if present
            if uri.startswith("+"):
                uri = uri[1:]

            # Should be digits only
            if uri.isdigit():
                return uri

        # Handle direct number format: +1234567890
        if uri.startswith("+"):
            uri = uri[1:]
            if uri.isdigit():
                return uri

        # Handle direct digits
        if uri.isdigit():
            return uri

        return None
    except Exception as e:
        logging.error(f"Error extracting number from URI {uri}: {e}")
        return None



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
    
    # NOTE: The 'transcription_node' method was removed as it was not a 
    # valid agent override and was not being called. Transcript logging
    # is likely handled by your SessionManager.


async def entrypoint(ctx: JobContext):
    # Setup conversation logging
    config.setup_conversation_log()

    # -----------------------------------------------------------------
    # --- CORRECTED RECORDING BLOCK ---
    # -----------------------------------------------------------------
    lkapi = None  # Define lkapi outside try block for cleanup
    try:
        logging.info(f"Attempting to start recording for room: {ctx.room.name}")
        
        # Environment variables are already loaded from the top of the script
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        # --- NEW DEBUG LOGGING ---
        # Log the values to confirm they are loaded correctly inside the entrypoint
        logging.info(f"Recording: URL={livekit_url}, KEY={livekit_api_key}")
        if livekit_api_secret:
            # Mask the secret for security, just show the first and last 4 chars
            logging.info(f"Recording: SECRET={livekit_api_secret[:4]}...{livekit_api_secret[-4:]}")
        else:
            logging.info("Recording: SECRET=None")
        # --- END DEBUG LOGGING ---

        if not all([livekit_url, livekit_api_key, livekit_api_secret]):
            logging.error("Cannot start recording: LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET not set.")
        else:
            # The API client needs an HTTP/S host, not WS/S
            http_host = livekit_url.replace("ws://", "http://").replace("wss://", "https://")

            # --- NEW DEBUG LOGGING ---
            logging.info(f"Recording: Initializing LiveKitAPI with host: {http_host}")
            # --- END DEBUG LOGGING ---

            # 1. Create the main API client
            lkapi = LiveKitAPI(http_host, livekit_api_key, livekit_api_secret)

            # 2. Use a unique filename with an AUDIO extension
            filename = f"recordings/{ctx.room.name}-{int(time.time())}.opus"

            # 3. Create the file output request
            file_output = EncodedFileOutput(
                filepath=filename
                # No azure block is needed; it uses your egress.yaml config
            )

            # 4. Create the main egress request
            request = RoomCompositeEgressRequest(
                room_name=ctx.room.name,
                audio_only=True,  # This creates the combined audio file
                file_outputs=[file_output]
            )

            # 5. Start the recording
            info = await lkapi.egress.start_room_composite_egress(request)
            logging.info(f"Successfully started recording. Egress ID: {info.egress_id}, File: {filename}")

    except Exception as e:
        logging.error(f"Failed to start recording for room {ctx.room.name}: {e}")
        # Log the error but continue the call. Recording is not a critical failure.
    finally:
        # 6. Clean up the client
        if lkapi:
            await lkapi.aclose() # Use aclose() for async
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
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")  # Minimal error handling agent

        # Start session with dummy agent
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )

        # Play error message and hang up
        await session.say("Sorry, we could not identify your call. Please try again.")
        await hangup_call()
        return

    logging.info(f"Extracted dialed number: {dialed_number}")

    # Load persona configuration from dialed number
    try:
        agent_instructions, session_instructions, closing_message, persona_name, full_config = await load_persona_from_dialed_number(dialed_number)
        logging.info(f"Successfully loaded persona for dialed number {dialed_number}: {persona_name}")
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
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")  # Minimal error handling agent

        # Start session with dummy agent
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )

        # Play error message and hang up
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
        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")  # Minimal error handling agent

        # Start session with dummy agent
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )

        # Play error message and hang up
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

        dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")  # Minimal error handling agent

        # Start session with dummy agent
        await session.start(
            room=ctx.room,
            agent=dummy_agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )

        # Play apology message and hang up
        await session.say("Sorry, currently the agent is not available. Please try later.")
        await hangup_call()
        return

    # NEW: Create the hangup event (our digital flag)
    hangup_event = asyncio.Event()

    # NEW: Create an instance of our HangupTool, giving it the event
    hangup_tool = HangupTool(hangup_event=hangup_event)

    # Continue with normal flow if validation passes
    # Create agent with persona instructions from the start
    agent = Assistant(custom_instructions=agent_instructions, end_call_tool=hangup_tool.end_call)
    logging.info(f"Created agent with persona instructions for: {persona_name}")

    # Get default AI service instances
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
    logging.info("SessionManager created successfully")

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

    # --- FINAL REVISED CONVERSATION LOGIC ---

    logging.info("Agent is running, waiting for user input or hangup signal...")

    # Generate the initial reply to start the conversation
    await session.generate_reply(instructions=initial_instruction)

    # Now wait for the hangup signal (the agent framework handles ongoing conversation)
    await hangup_event.wait()

    # --- END OF REVISED BLOCK ---

    logging.info("Hangup signal received.")

    # --- HANGUP SEQUENCE ---
    # Play the pre-defined closing message from the persona config
    if closing_message:
        logging.info(f"Playing closing message: {closing_message}")
        await session.say(closing_message)

    await hangup_call()
    logging.info("Call has been successfully terminated.")
    # No need for return, the function will end naturally


if __name__ == "__main__":
    # --- CORRECTED MAIN BLOCK ---
    # This single call initializes the worker options, parses
    # CLI arguments (like 'dev' for watch mode), and runs the agent.
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="friday-assistant"
        )
    )