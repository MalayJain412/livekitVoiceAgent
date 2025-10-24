"""
Session Manager
Handles session lifecycle, logging, and history tracking
"""

import asyncio
import re
import json
import logging
from datetime import datetime
from pathlib import Path
import os
from datetime import timedelta
from typing import Optional

from livekit.agents import AgentSession
from livekit.agents.job import get_job_context
from livekit import api

from transcript_logger import (
    log_event,
    get_log_path,
    flush_and_stop,
    generate_session_id,
    save_conversation_session,
)

# Configurable hangup timings (seconds)
# AUTO_HANGUP_WAIT_SECONDS: time to wait after assistant closing message (default 4)
# HANGUP_ON_REQUEST_WAIT_SECONDS: time to wait after explicit user request to hang up (default 2)
try:
    AUTO_HANGUP_WAIT_SECONDS = int(os.getenv("AUTO_HANGUP_WAIT_SECONDS", "4"))
except Exception:
    AUTO_HANGUP_WAIT_SECONDS = 4

try:
    HANGUP_ON_REQUEST_WAIT_SECONDS = int(os.getenv("HANGUP_ON_REQUEST_WAIT_SECONDS", "2"))
except Exception:
    HANGUP_ON_REQUEST_WAIT_SECONDS = 2

# Configurable hangup phrases for explicit user requests
# HANGUP_PHRASES: comma-separated list of phrases to detect user hangup requests
DEFAULT_HANGUP_PHRASES = [
    "please hang up", "hang up the call", "hang up", "please hangup", 
    "end the call", "disconnect the call", "terminate the call",
    "please disconnect", "cut the call", "finish the call",
    "end this call", "please end the call", "can you hang up",
    "can you end the call", "disconnect", "bye bye", "goodbye",
    "sign the call", "please sign the call", "sign off", "end call"
]

try:
    hangup_phrases_env = os.getenv("HANGUP_PHRASES", "")
    if hangup_phrases_env.strip():
        HANGUP_PHRASES = [phrase.strip().lower() for phrase in hangup_phrases_env.split(",") if phrase.strip()]
    else:
        HANGUP_PHRASES = [phrase.lower() for phrase in DEFAULT_HANGUP_PHRASES]
except Exception:
    HANGUP_PHRASES = [phrase.lower() for phrase in DEFAULT_HANGUP_PHRASES]

logging.info(f"SessionManager configured with {len(HANGUP_PHRASES)} hangup phrases: {HANGUP_PHRASES[:3]}...")  # Show first 3 for brevity


class SessionManager:
    def __init__(self, session: AgentSession):
        self.session = session
        self.watch_task: Optional[asyncio.Task] = None
        # For hangup-after-closing behaviour
        self.hangup_task: Optional[asyncio.Task] = None
        self.last_user_activity: Optional[datetime] = None
        self._closing_detected_time: Optional[datetime] = None
        
    async def setup_session_logging(self):
        """Setup session logging and generate session ID"""
        try:
            sid = generate_session_id()
            logging.info(f"Transcript logging session id: {sid}")
        except Exception:
            pass
    
    async def setup_shutdown_callback(self):
        """Setup shutdown callback to save final session history - SIMPLIFIED VERSION"""
        async def _save_history_on_shutdown():
            try:
                # Extract session history
                try:
                    payload = self.session.history.toJSON()
                except Exception:
                    try:
                        payload = self.session.history.to_json()
                    except Exception:
                        try:
                            payload = self.session.history.to_dict()
                        except Exception:
                            payload = str(self.session.history)

                # Save raw transcript (first file)
                timestamp = datetime.utcnow().isoformat().replace(":", "-")
                room_name = getattr(self.session, "room", None)
                room_name = getattr(room_name, "name", "session") if room_name else "session"
                fname = Path(get_log_path()).with_name(f"transcript_{room_name}_{timestamp}.json")
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                print(f"Transcript saved to {fname}")
                
                # Note: Do NOT call save_conversation_session here as flush_and_stop() will handle it
                
            except Exception as e:
                # fallback: log an event indicating save failed
                log_event({
                    "role": "system",
                    "event": "shutdown_save_failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            finally:
                # flush logger thread (this will trigger final save_conversation_session)
                try:
                    flush_and_stop()
                except Exception:
                    pass
                # cancel watcher if running
                try:
                    if self.watch_task is not None:
                        self.watch_task.cancel()
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
                self.session._aclose_impl = (lambda *a, **k: _save_history_on_shutdown())  # type: ignore
            except Exception:
                pass

    async def start_history_watcher(self):
        """Start background watcher that polls session.history and logs new committed items"""
        logging.info(f"SessionManager: starting history watcher with hangup phrases: {HANGUP_PHRASES}")
        logging.info(f"SessionManager: auto-hangup wait: {AUTO_HANGUP_WAIT_SECONDS}s, user request wait: {HANGUP_ON_REQUEST_WAIT_SECONDS}s")
        
        async def _watch_history_and_log():
            seen_ids = set()
            try:
                while True:
                    try:
                        hist = getattr(self.session, "history", None)
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

                                    # Fallback: some session_history items store details only in `raw`.
                                    raw_field = it.get("raw") if isinstance(it, dict) else None
                                    if (not role or role == "unknown") and raw_field:
                                        try:
                                            mrole = re.search(r"role='([^']+)'", str(raw_field))
                                            if mrole:
                                                role = mrole.group(1)
                                        except Exception:
                                            pass

                                    if (not content or content == "") and raw_field:
                                        try:
                                            # extract between content=[ ... ]
                                            m = re.search(r"content=\[(.*)\]", str(raw_field))
                                            if m:
                                                # strip surrounding quotes and join if comma-separated
                                                raw_content = m.group(1)
                                                # remove leading/trailing whitespace and quotes
                                                raw_content = raw_content.strip()
                                                # remove surrounding quotes if present
                                                if raw_content.startswith("'") and raw_content.endswith("'"):
                                                    raw_content = raw_content[1:-1]
                                                content = raw_content
                                        except Exception:
                                            pass

                                    evt = {
                                        "role": role,
                                        "content": content,
                                        "timestamp": datetime.utcnow().isoformat() + "Z",
                                        "source": "session_history",
                                        "item_type": it.get("type") if isinstance(it, dict) else None,
                                        "raw": it,
                                    }

                                    try:
                                        log_event(evt)
                                    except Exception:
                                        # never let logging break the watcher
                                        pass

                                    # --- Hangup-after-closing detection logic ---
                                    # COMMENT OUT OR DELETE THIS ENTIRE BLOCK
                                    # try:
                                    #     # Normalize role string
                                    #     r_lower = (role or "").lower()
                                    #
                                    #     # Treat user/human/caller/participant roles as activity
                                    #     if r_lower in ("user", "human", "caller", "participant"):
                                    #         # mark last user activity and cancel any pending hangup
                                    #         self.last_user_activity = datetime.utcnow()
                                    #         if self.hangup_task is not None:
                                    #             try:
                                    #                 logging.info("SessionManager: user activity detected — cancelling pending auto-hangup")
                                    #                 self.hangup_task.cancel()
                                    #             except Exception:
                                    #                 pass
                                    #         self.hangup_task = None
                                    #         self._closing_detected_time = None
                                    #
                                    #         # Check for explicit user request to hang up
                                    #         try:
                                    #             user_text = (content or "").strip().lower()
                                    #             logging.info(f"SessionManager: checking user text for hangup phrases: '{user_text}'")
                                    #             logging.info(f"SessionManager: configured hangup phrases: {HANGUP_PHRASES}")
                                    #             
                                    #             # Check against configurable phrase list
                                    #             matched_phrase = None
                                    #             for phrase in HANGUP_PHRASES:
                                    #                 if phrase in user_text:
                                    #                 matched_phrase = phrase
                                    #                 break
                                    #             
                                    #             if matched_phrase:
                                    #                 logging.info(f"SessionManager: explicit user hangup request detected (matched phrase: '{matched_phrase}') — scheduling immediate hangup wait")
                                    #                 
                                    #                 # Log hangup scheduling event
                                    #                 log_event({
                                    #                     "type": "auto_hangup_scheduled",
                                    #                     "trigger": "user_request",
                                    #                     "matched_phrase": matched_phrase,
                                    #                     "wait_seconds": HANGUP_ON_REQUEST_WAIT_SECONDS,
                                    #                     "room": getattr(getattr(self.session, "room", None), "name", None),
                                    #                     "timestamp": datetime.utcnow().isoformat() + "Z"
                                    #                 })
                                    #                 
                                    #                 # schedule a short wait then hangup
                                    #                 t = datetime.utcnow()
                                    #                 # cancel any existing hangup task
                                    #                 if self.hangup_task is not None:
                                    #                     try:
                                    #                         self.hangup_task.cancel()
                                    #                     except Exception:
                                    #                         pass
                                    #                 self.hangup_task = asyncio.create_task(self._hangup_wait_and_end(t, wait_seconds=HANGUP_ON_REQUEST_WAIT_SECONDS))
                                    #             else:
                                    #                 logging.info(f"SessionManager: no hangup phrase found in user text: '{user_text}'")
                                    #         except Exception as e:
                                    #             logging.error(f"SessionManager: error in hangup phrase detection: {e}")
                                    #             # swallow failures in explicit request parsing
                                    #             pass
                                    #
                                    #     # If assistant/agent/system spoke, check for closing message trigger
                                    #     elif r_lower in ("assistant", "agent", "system") and content:
                                    #         closing_msg = getattr(self.session, "closing_message", None)
                                    #         if closing_msg:
                                    #             # simple containment check (case-insensitive)
                                    #             try:
                                    #                 if closing_msg.strip().lower() in content.strip().lower() or content.strip().lower() in closing_msg.strip().lower():
                                    #                     closing_time = datetime.utcnow()
                                    #                     self._closing_detected_time = closing_time
                                    #                     # cancel any existing hangup_task then start a new one
                                    #                     if self.hangup_task is not None:
                                    #                         try:
                                    #                             logging.info("SessionManager: restarting auto-hangup task due to new closing message")
                                    #                             self.hangup_task.cancel()
                                    #                             except Exception:
                                    #                                 pass
                                    #                         # start background wait-and-hangup
                                    #                         logging.info(f"SessionManager: detected closing message — scheduling auto-hangup in {AUTO_HANGUP_WAIT_SECONDS}s unless user replies")
                                    #                         
                                    #                         # Log hangup scheduling event
                                    #                         log_event({
                                    #                             "type": "auto_hangup_scheduled",
                                    #                             "trigger": "closing_message",
                                    #                             "wait_seconds": AUTO_HANGUP_WAIT_SECONDS,
                                    #                             "room": getattr(getattr(self.session, "room", None), "name", None),
                                    #                             "persona": getattr(self.session, "persona_name", None),
                                    #                             "timestamp": datetime.utcnow().isoformat() + "Z"
                                    #                         })
                                    #                         
                                    #                         self.hangup_task = asyncio.create_task(self._hangup_wait_and_end(closing_time, wait_seconds=AUTO_HANGUP_WAIT_SECONDS))
                                    #             except Exception:
                                    #                 pass
                                    # except Exception:
                                    #     pass
                                    # --- END OF BLOCK TO REMOVE ---
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
            self.watch_task = asyncio.create_task(_watch_history_and_log())
        except Exception:
            self.watch_task = None
    
    def log_persona_applied_event(self, persona_name: str, full_config: Optional[dict], 
                                  session_instructions: Optional[str], closing_message: Optional[str]):
        """Log persona application event for transcript tracking"""
        try:
            log_event({
                "type": "persona_applied",
                "persona_name": persona_name,
                "has_config": full_config is not None,
                "has_session_instructions": session_instructions is not None,
                "has_closing": closing_message is not None,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
        except Exception:
            pass

    async def _hangup_wait_and_end(self, detected_at: datetime, wait_seconds: int = 10):
        """Wait wait_seconds and end the room if no user activity detected since the closing message.

        This coroutine is started when a closing message is detected. If any user activity
        (messages with role user/human/caller) is observed before the timer elapses, the
        hangup_task is cancelled by the watcher loop.
        """
        try:
            room_name = getattr(getattr(self.session, "room", None), "name", None)
            logging.info(f"SessionManager: auto-hangup wait started for room={room_name}, wait_seconds={wait_seconds}")
            logging.debug(f"SessionManager: hangup detected_at={detected_at}, last_user_activity={self.last_user_activity}")
            
            # Sleep for the configured wait duration in short intervals so cancellation is responsive
            slept = 0.0
            interval = 0.5
            while slept < wait_seconds:
                await asyncio.sleep(interval)
                slept += interval

                # If there was user activity after the closing detection, abort hangup
                if self.last_user_activity and self.last_user_activity > detected_at:
                    logging.info("SessionManager: user activity detected after closing message — aborting auto-hangup")
                    return

            # Final sanity check before hangup: ensure no recent user activity
            if self.last_user_activity and self.last_user_activity > detected_at:
                logging.info("SessionManager: final check - user activity after closing, aborting hangup")
                return

            # Perform hangup via JobContext API (delete_room)
            try:
                logging.info(f"SessionManager: no user reply detected for {wait_seconds}s after closing — performing auto-hangup for room {room_name}")
                
                # Use the same hangup approach as validation.py
                await self._perform_hangup()
                
                # Log structured auto_hangup event
                log_event({
                    "type": "auto_hangup",
                    "reason": "closing_message_no_reply" if wait_seconds == AUTO_HANGUP_WAIT_SECONDS else "user_request_no_activity",
                    "room": room_name,
                    "wait_seconds": wait_seconds,
                    "persona": getattr(self.session, "persona_name", None),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "success": True
                })
                
                logging.info(f"SessionManager: auto-hangup completed successfully for room {room_name}")
                
            except Exception as e:
                # Log failed auto_hangup event
                log_event({
                    "type": "auto_hangup_failed", 
                    "reason": "api_error",
                    "room": room_name,
                    "wait_seconds": wait_seconds,
                    "persona": getattr(self.session, "persona_name", None),
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                logging.warning(f"Failed to auto hangup room: {e}")

        except asyncio.CancelledError:
            # Task was cancelled due to user activity; nothing to do
            return
        except Exception:
            # swallow any unexpected exceptions to avoid crashing watcher
            return

    async def _perform_hangup(self):
        """
        Perform hangup using the same approach as validation.py hangup_call()
        """
        ctx = get_job_context()
        if ctx is None:
            logging.warning("SessionManager: No job context available for hangup")
            return
        
        try:
            # Before ending the room, wait for any active agent speech to finish
            try:
                current_speech = getattr(self.session, "current_speech", None)
                if current_speech is not None:
                    logging.info("SessionManager: waiting for current speech to finish before hangup")
                    # Prefer explicit wait_for_playout API if available
                    if hasattr(current_speech, "wait_for_playout"):
                        try:
                            await current_speech.wait_for_playout()
                        except Exception:
                            # fallback to awaiting the handle directly
                            try:
                                await current_speech
                            except Exception:
                                pass
                    else:
                        try:
                            await current_speech
                        except Exception:
                            pass
            except Exception as e:
                logging.warning(f"SessionManager: failed waiting for speech to finish: {e}")

            logging.debug(f"SessionManager: calling delete_room for {ctx.room.name}")
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
            logging.info("SessionManager: Call hung up successfully")
            
        except Exception as e:
            logging.error(f"SessionManager: Error hanging up call: {e}")
            raise  # Re-raise to be caught by caller