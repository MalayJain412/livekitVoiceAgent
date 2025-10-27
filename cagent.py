import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio
from typing import Optional, Tuple

load_dotenv()  # Load environment variables early

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

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)
    
# async def get_sip_participant_and_number(ctx: JobContext) -> Tuple[Optional[str], Optional[str]]:
#     """Extract SIP participant and dialed number from the room (prefer dialed number)."""
#     try:
#         if hasattr(ctx.room, "participants") and ctx.room.participants:
#             participants = ctx.room.participants

#             for participant in participants.values():
#                 if participant.identity.startswith("sip_"):
#                     # Prefer lk_sip_to (dialed number)
#                     if hasattr(participant, "attributes") and participant.attributes:
#                         dialed_number_attr = participant.attributes.get("lk_sip_to")
#                         caller_number_attr = participant.attributes.get("lk_sip_from")

#                         # 1️⃣ Try dialed number first
#                         if dialed_number_attr:
#                             dialed_number = _extract_number_from_sip_uri(dialed_number_attr)
#                             if dialed_number:
#                                 logging.info(f"Extracted dialed number from participant attributes: {dialed_number}")
#                                 return participant.identity, dialed_number

#                         # 2️⃣ Fallback to caller number if dialed number unavailable
#                         if caller_number_attr:
#                             caller_number = _extract_number_from_sip_uri(caller_number_attr)
#                             if caller_number:
#                                 logging.info(f"Fallback to caller number: {caller_number}")
#                                 return participant.identity, caller_number

#                     # 3️⃣ Last fallback: try parsing participant.identity directly
#                     parsed_number = _extract_number_from_sip_uri(participant.identity)
#                     if parsed_number:
#                         logging.info(f"Extracted number from participant identity: {parsed_number}")
#                         return participant.identity, parsed_number

#         # 4️⃣ Final fallback: Extract from room name
#         room_name = ctx.room.name
#         logging.info(f"Trying fallback extraction from room name: {room_name}")

#         # Example formats:
#         #   number-+918123456789 or friday-call-+918123456789_abcXYZ
#         for prefix in ["number-", "friday-call-", "callee-"]:
#             if room_name.startswith(prefix):
#                 number_part = room_name.replace(prefix, "").split("_")[0]
#                 dialed_number = _extract_number_from_sip_uri(number_part)
#                 if dialed_number:
#                     logging.info(f"Extracted dialed number from room name: {dialed_number}")
#                     return None, dialed_number

#         logging.warning("No dialed number found in participants or room name.")
#         return None, None

#     except Exception as e:
#         logging.error(f"Error extracting SIP participant and number: {e}")
#         return None, None

# def _extract_number_from_sip_uri(uri: str) -> Optional[str]:
#     """Extract phone number from SIP URI format or participant identity."""
#     try:
#         if uri.startswith("sip_"):
#             uri = uri[4:]
#             if uri.startswith("+"):
#                 uri = uri[1:]
#             if uri.isdigit():
#                 return uri

#         if uri.startswith("sip:"):
#             uri = uri[4:]
#             if "@" in uri:
#                 uri = uri.split("@")[0]
#             if uri.startswith("+"):
#                 uri = uri[1:]
#             if uri.isdigit():
#                 return uri

#         if uri.startswith("+"):
#             uri = uri[1:]
#             if uri.isdigit():
#                 return uri

#         if uri.isdigit():
#             return uri

#         return None
#     except Exception as e:
#         logging.error(f"Error extracting number from URI {uri}: {e}")
#         return None


import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio
from typing import Optional, Tuple
import re

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
    
    # Capture realtime transcriptions via transcription_node (called by AgentSession)
    async def transcription_node(self, text, model_settings):
        from transcript_logger import log_user_message
        # text is an async iterable of strings or TimedString-like objects
        async for chunk in text:
            try:
                # TimedString may have text, start_time, end_time
                if hasattr(chunk, "text"):
                    content = getattr(chunk, "text")
                    meta = {
                        "start_time": getattr(chunk, "start_time", None),
                        "end_time": getattr(chunk, "end_time", None),
                    }
                    log_user_message(content, source="transcription_node", meta=meta)
                else:
                    # plain string
                    log_user_message(str(chunk), source="transcription_node")
            except Exception:
                # swallow to avoid breaking pipeline
                pass

            yield chunk


async def entrypoint(ctx: JobContext):
    # Setup conversation logging
    config.setup_conversation_log()
    
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
    opts = agents.cli.run_app(agents.WorkerOptions
        (
        entrypoint_fnc=entrypoint,
        agent_name="friday-assistant"
        )
    )
    agents.cli.run_app(opts)
