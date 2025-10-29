import os
from dotenv import load_dotenv
import logging
import logging.handlers
from logging_config import configure_logging
import asyncio
import json
from typing import Optional, Tuple
import re
import time
import aiohttp  # For async HTTP requests
import aiofiles  # For async file operations
from datetime import datetime, timedelta
from pathlib import Path
load_dotenv()  # Load environment variables early

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero
from prompts import set_agent_instruction
from persona_handler import load_persona_from_dialed_number as load_persona_from_api
from tools import (
    create_lead, 
    detect_lead_intent, 
    HangupTool
)
import config
from instances import get_instances_from_payload
from session_manager import SessionManager
from validation import validate_agent_availability, hangup_call
from crm_upload import upload_call_data_from_conversation

try:
    from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput
except ImportError:
    logging.critical("Could not import LiveKitAPI. Please run: pip install livekit-api")

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

def setup_production_logging():
    """Setup comprehensive logging for production debugging"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # CRM-specific logger
    crm_logger = logging.getLogger('CRM_UPLOAD')
    crm_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "crm_uploads.log",
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    crm_handler.setFormatter(detailed_formatter)
    crm_logger.addHandler(crm_handler)
    
    # Session logger for call tracking
    session_logger = logging.getLogger('SESSION_TRACKING')
    session_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "sessions.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    session_handler.setFormatter(detailed_formatter)
    session_logger.addHandler(session_handler)
    
    logging.info(f"Production logging setup completed - Log files: {logs_dir.absolute()}")

# Setup production logging
setup_production_logging()


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


async def upload_call_data_to_crm(
    recording_url: str,
    recording_size: int,
    dialed_number: str,
    full_config: dict,
    session_manager=None
):
    """
    Upload complete call data (recording, transcript, leads) to CRM API using
    the working MongoDB conversation format.
    
    Args:
        recording_url: URL of the uploaded recording
        recording_size: Size of recording file in bytes
        dialed_number: Phone number that was dialed
        full_config: Full persona configuration from API
        session_manager: SessionManager instance for accessing session data
    """
    try:
        # Extract campaign details from persona config
        campaigns = full_config.get("campaigns", [])
        if not campaigns:
            logging.warning("No campaigns found in persona config - skipping CRM upload")
            return False
            
        campaign = campaigns[0]
        campaign_id = campaign.get("_id")
        
        voice_agents = campaign.get("voiceAgents", [])
        if not voice_agents:
            logging.warning("No voice agents found in campaign - skipping CRM upload")
            return False
            
        voice_agent = voice_agents[0]
        voice_agent_id = voice_agent.get("_id")
        
        # Get client ID from campaign
        client_id = campaign.get("client")
        
        if not all([campaign_id, voice_agent_id, client_id]):
            logging.warning(f"Missing required IDs for CRM upload: campaign_id={campaign_id}, voice_agent_id={voice_agent_id}, client_id={client_id}")
            return False
        
        # Generate call ID with session reference
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        session_id = getattr(session_manager, 'session_id', 'unknown') if session_manager else 'unknown'
        call_id = f"CALL-{timestamp}-{session_id[-8:] if session_id else dialed_number.replace('+', '')[-8:]}"
        
        # Get the most recent conversation file from session manager
        conversation_data = None
        if session_manager:
            try:
                # Get the conversation file path that was saved
                conversation_file = getattr(session_manager, 'conversation_file_path', None)
                if conversation_file and os.path.exists(conversation_file):
                    with open(conversation_file, 'r', encoding='utf-8') as f:
                        conversation_data = json.load(f)
                    logging.info(f"Loaded conversation data from: {conversation_file}")
                else:
                    logging.warning(f"Conversation file not found: {conversation_file}")
                    
            except Exception as e:
                logging.warning(f"Could not load conversation data from session: {e}")
        
        # If no conversation data found, skip CRM upload
        if not conversation_data:
            logging.warning("No conversation data available - skipping CRM upload")
            return False
        
        logging.info(f"Uploading call data to CRM - Call ID: {call_id}")
        
        # Use the working CRM upload function with MongoDB format
        success = await upload_call_data_from_conversation(
            campaign_id=campaign_id,
            voice_agent_id=voice_agent_id,
            client_id=client_id,
            call_id=call_id,
            caller_phone=dialed_number,
            conversation_data=conversation_data,
            recording_url=recording_url,
            recording_size=recording_size,
            direction="inbound",
            status="completed"
        )
        
        if success:
            logging.info(f"Successfully uploaded call data to CRM for call {call_id}")
        else:
            logging.error(f"Failed to upload call data to CRM for call {call_id}")
            
        return success
        
    except Exception as e:
        logging.error(f"Error uploading call data to CRM: {e}", exc_info=True)
        return False


async def entrypoint(ctx: JobContext):
    # Setup conversation logging
    config.setup_conversation_log()
    
    # Log call start
    session_logger = logging.getLogger('SESSION_TRACKING')
    session_logger.info(f"CALL_START: Room={ctx.room.name}, Participants={ctx.room.num_participants}")
    
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

    # --- Main Agent Logic ---
    try:
        # Extract dialed number from SIP participant in the room
        participant_identity, dialed_number = await get_sip_participant_and_number(ctx)
        
        session_logger = logging.getLogger('SESSION_TRACKING')
        
        if not dialed_number:
            session_logger.error(f"EXTRACTION_FAILED: Could not extract dialed number from room {ctx.room.name}")
            logging.error("Critical: Could not extract dialed number. Aborting call setup.")
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
        
        session_logger.info(f"EXTRACTED_NUMBER: {dialed_number} from room {ctx.room.name}")
        logging.info(f"Extracted dialed number: {dialed_number}")
        
        # Load persona configuration from dialed number
        try:
            agent_instructions, session_instructions, closing_message, persona_name, full_config = await load_persona_from_dialed_number(dialed_number)
            session_logger.info(f"PERSONA_LOADED: {persona_name} for number {dialed_number}")
            logging.info(f"Successfully loaded persona for dialed number {dialed_number}: {persona_name}")
        except ValueError as e:
            session_logger.warning(f"PERSONA_VALIDATION_FAILED: {dialed_number} - {e}")
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
            session_logger.error(f"PERSONA_LOAD_ERROR: {dialed_number} - {e}")
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
            session_logger.warning(f"AGENT_UNAVAILABLE: {failure_reason} for {dialed_number}")
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
        session_logger.info(f"SESSION_STARTING: {getattr(session_manager, 'session_id', 'unknown')}")
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

    except Exception as e:
        # Catch errors during the main agent loop
        logging.error(f"Error during agent execution: {e}", exc_info=True)
        # Attempt graceful hangup even if error occurs
        try:
            await hangup_call()
        except Exception as hangup_err:
            logging.error(f"Error during final hangup attempt: {hangup_err}")

    logging.info("Agent entrypoint finished.")


if __name__ == "__main__":
    # --- Corrected: Call run_app only once ---
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="friday-assistant"
        )
    )
