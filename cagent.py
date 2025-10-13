import os
from dotenv import load_dotenv
import logging
import asyncio

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import deepgram, noise_cancellation, silero

# FRIDAY AI: Import plugins at module level to register them on main thread
from livekit.plugins import google, cartesia

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, triotech_info, create_lead, detect_lead_intent
import config
import json
from pathlib import Path
from transcript_logger import log_user_message, log_event, get_log_path, flush_and_stop
from livekit.agents.job import get_job_context

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Make the LLM model configurable via environment so we don't have to edit code
# each time. Defaults to a newer Flash model; change by setting LLM_MODEL in .env
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")


class Assistant(Agent):
    def __init__(self):
        # FRIDAY AI: Use Google LLM directly
        llm_instance = google.LLM(model=LLM_MODEL, temperature=0.8)
            
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=llm_instance,
            tools=[get_weather, search_web, triotech_info, create_lead, detect_lead_intent],
        )

    # Capture realtime transcriptions via transcription_node (called by AgentSession)
    async def transcription_node(self, text, model_settings):
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
    # Ensure conversations directory exists (config.setup_conversation_log is now a no-op file-creator)
    _ = config.setup_conversation_log()
    
    agent = Assistant()

    # FRIDAY AI: Use plugins directly
    llm_instance = google.LLM(model=LLM_MODEL, temperature=0.8)
    tts_instance = cartesia.TTS(
        model="sonic-2",
        language="hi",
        voice="f91ab3e6-5071-4e15-b016-cde6f2bcd222",
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=llm_instance,
        tts=tts_instance,
        vad=silero.VAD.load(),
    )

    # Background watcher task reference (set after session.start)
    watch_task = None

    # Attach shutdown callback to save final session.history
    async def _save_history_on_shutdown():
        try:
            # session.history may expose toJSON/to_json; try several options
            try:
                payload = session.history.toJSON()
            except Exception:
                try:
                    payload = session.history.to_json()
                except Exception:
                    try:
                        payload = session.history.to_dict()
                    except Exception:
                        payload = str(session.history)

            timestamp = __import__("datetime").datetime.utcnow().isoformat().replace(":", "-")
            room_name = getattr(session, "room", None)
            room_name = getattr(room_name, "name", "session") if room_name else "session"
            fname = Path(get_log_path()).with_name(f"transcript_{room_name}_{timestamp}.json")
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"Transcript saved to {fname}")
        except Exception as e:
            # fallback: log an event indicating save failed
            log_event({
                "role": "system",
                "event": "shutdown_save_failed",
                "error": str(e),
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            })
        finally:
            # flush logger thread
            try:
                flush_and_stop()
            except Exception:
                pass
            # cancel watcher if running
            try:
                if watch_task is not None:
                    watch_task.cancel()
            except Exception:
                pass

    # Register shutdown saver on the JobContext (job-level shutdown hook)
    try:
        job_ctx = get_job_context()
        job_ctx.add_shutdown_callback(_save_history_on_shutdown)
    except Exception:
        # If we cannot get job context (unlikely in entrypoint), fallback to session aclose hook
        try:
            # attach to session close as best-effort
            session._aclose_impl = (lambda *a, **k: _save_history_on_shutdown())  # type: ignore
        except Exception:
            pass

    await session.start(
        room=ctx.room,
        agent=agent,
        room_output_options=RoomOutputOptions(audio_enabled=True),
    )

    # Start a background watcher that polls session.history and logs new committed items
    async def _watch_history_and_log():
        seen_ids = set()
        try:
            while True:
                try:
                    hist = getattr(session, "history", None)
                    items = None
                    if hist is None:
                        items = None
                    else:
                        # Prefer attribute access
                        if hasattr(hist, "items"):
                            items = getattr(hist, "items")
                        else:
                            # Try a few serializer methods
                            try:
                                d = hist.to_dict()
                                items = d.get("items") if isinstance(d, dict) else None
                            except Exception:
                                try:
                                    d = hist.to_json()
                                    import json as _json
                                    dd = _json.loads(d) if isinstance(d, str) else d
                                    items = dd.get("items") if isinstance(dd, dict) else None
                                except Exception:
                                    try:
                                        d = hist.toJSON()
                                        import json as _json2
                                        dd = _json2.loads(d) if isinstance(d, str) else d
                                        items = dd.get("items") if isinstance(dd, dict) else None
                                    except Exception:
                                        items = None

                    if items:
                        for it in items:
                            try:
                                # item id if present
                                itid = None
                                if isinstance(it, dict):
                                    itid = it.get("id")
                                else:
                                    itid = str(it)
                                if itid in seen_ids:
                                    continue
                                seen_ids.add(itid)

                                # extract role and content
                                role = it.get("role") if isinstance(it, dict) else "unknown"
                                content = it.get("content") if isinstance(it, dict) else None
                                if isinstance(content, list):
                                    content = " ".join([str(c) for c in content])
                                elif content is None:
                                    content = ""

                                evt = {
                                    "role": role,
                                    "content": content,
                                    "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                                    "source": "session_history",
                                    "item_type": it.get("type") if isinstance(it, dict) else None,
                                    "raw": it,
                                }

                                try:
                                    log_event(evt)
                                except Exception:
                                    # never let logging break the watcher
                                    pass
                            except Exception:
                                # individual item failure should not stop the watcher
                                pass
                except Exception:
                    # swallow
                    pass
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return

    # create and start watcher task
    try:
        watch_task = asyncio.create_task(_watch_history_and_log())
    except Exception:
        watch_task = None

    await session.generate_reply(instructions=SESSION_INSTRUCTION)
    await asyncio.Future()  # Run until externally stopped


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
