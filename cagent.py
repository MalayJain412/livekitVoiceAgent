import os
from dotenv import load_dotenv
import logging
import asyncio

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, triotech_info, create_lead, detect_lead_intent
import config
from instances import get_default_instances
from persona_handler import (
    load_persona_from_metadata, 
    apply_persona_to_agent, 
    attach_persona_to_session
)
from session_manager import SessionManager


load_dotenv()
logging.basicConfig(level=logging.INFO)


class Assistant(Agent):
    def __init__(self):
        instances = get_default_instances()
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=instances["llm"],
            tools=[get_weather, search_web, triotech_info, create_lead, detect_lead_intent],
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
    
    # Load persona configuration from job metadata
    agent_instructions, welcome_message, closing_message, persona_name, full_config = load_persona_from_metadata(ctx)
    
    # Create agent and apply persona
    agent = Assistant()
    apply_persona_to_agent(agent, agent_instructions, persona_name)

    # Get default AI service instances
    instances = get_default_instances()
    
    session = AgentSession(
        stt=instances["stt"],
        llm=instances["llm"],
        tts=instances["tts"],
        vad=instances["vad"],
    )

    # Attach persona configuration to session
    attach_persona_to_session(session, full_config, persona_name, welcome_message, closing_message)
    
    # Initialize session manager
    session_manager = SessionManager(session)
    
    # Setup session logging and monitoring
    await session_manager.setup_session_logging()
    await session_manager.setup_shutdown_callback()

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
        room_output_options=RoomOutputOptions(audio_enabled=True),
    )

    # Log persona application event
    session_manager.log_persona_applied_event(persona_name, full_config, welcome_message, closing_message)
    
    # Start background history watcher
    await session_manager.start_history_watcher()

    await session.generate_reply(instructions=SESSION_INSTRUCTION)
    await asyncio.Future()  # Run until externally stopped


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
