"""
Session Manager
Handles session lifecycle, logging, and history tracking
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from livekit.agents import AgentSession
from livekit.agents.job import get_job_context

from transcript_logger import (
    log_event,
    get_log_path,
    flush_and_stop,
    generate_session_id,
    save_conversation_session,
)


class SessionManager:
    def __init__(self, session: AgentSession):
        self.session = session
        self.watch_task: Optional[asyncio.Task] = None
        
    async def setup_session_logging(self):
        """Setup session logging and generate session ID"""
        try:
            sid = generate_session_id()
            logging.info(f"Transcript logging session id: {sid}")
        except Exception:
            pass
    
    async def setup_shutdown_callback(self):
        """Setup shutdown callback to save final session history"""
        async def _save_history_on_shutdown():
            try:
                # session.history may expose toJSON/to_json; try several options
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

                timestamp = datetime.utcnow().isoformat().replace(":", "-")
                room_name = getattr(self.session, "room", None)
                room_name = getattr(room_name, "name", "session") if room_name else "session"
                fname = Path(get_log_path()).with_name(f"transcript_{room_name}_{timestamp}.json")
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                print(f"Transcript saved to {fname}")
                
                # Attempt to extract items list and persist full conversation session
                try:
                    items = None
                    if isinstance(payload, dict):
                        items = payload.get("items")
                    elif isinstance(payload, str):
                        try:
                            parsed = json.loads(payload)
                            if isinstance(parsed, dict):
                                items = parsed.get("items")
                        except Exception:
                            items = None

                    if items:
                        try:
                            meta = {"room": getattr(self.session.room, "name", None)} if getattr(self.session, "room", None) else {}
                            saved = save_conversation_session(items, metadata=meta)
                            if saved:
                                logging.info(f"Conversation session saved: {saved}")
                        except Exception as e:
                            logging.error(f"Failed to save conversation session: {e}")
                except Exception:
                    pass
            except Exception as e:
                # fallback: log an event indicating save failed
                log_event({
                    "role": "system",
                    "event": "shutdown_save_failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            finally:
                # flush logger thread
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
                                  welcome_message: Optional[str], closing_message: Optional[str]):
        """Log persona application event for transcript tracking"""
        try:
            log_event({
                "type": "persona_applied",
                "persona_name": persona_name,
                "has_config": full_config is not None,
                "has_welcome": welcome_message is not None,
                "has_closing": closing_message is not None,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
        except Exception:
            pass