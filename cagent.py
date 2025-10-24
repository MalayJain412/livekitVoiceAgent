import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio

load_dotenv()  # Load environment variables early

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
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
from persona_handler import (
    load_persona_with_fallback, 
    apply_persona_to_agent, 
    attach_persona_to_session,
    should_use_local_persona
)
from session_manager import SessionManager
from validation import validate_agent_availability, hangup_call

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)


class Assistant(Agent):
    def __init__(self, custom_instructions=None, end_call_tool=None):
        # Use custom instructions if provided, otherwise use default
        instructions = custom_instructions if custom_instructions else AGENT_INSTRUCTION

        super().__init__(
            instructions=instructions,
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
    
    # Load persona configuration with fallback to API
    agent_instructions, session_instructions, closing_message, persona_name, full_config = await load_persona_with_fallback(ctx)
    
    # VALIDATION: Check agent availability before proceeding (only for API mode)
    if not should_use_local_persona():
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
            
            dummy_agent = Assistant(custom_instructions="")  # Minimal placeholder agent
            
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
    else:
        logging.info("PERSONA_USE=local: Skipping validation checks, allowing all calls to proceed")
    
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
    if session_instructions:
        # Use persona's conversation structure for session behavior
        initial_instruction = session_instructions
        logging.info(f"Using persona session instructions for: {persona_name}")
    else:
        # Use default session instruction
        initial_instruction = SESSION_INSTRUCTION
        logging.info("Using default session instruction")
    
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
