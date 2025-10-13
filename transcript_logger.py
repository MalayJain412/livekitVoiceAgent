import os
import json
import threading
import queue
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DEFAULT_DIR = Path(__file__).parent / "conversations"
DEFAULT_DIR.mkdir(exist_ok=True)
DEFAULT_FILE = DEFAULT_DIR / "transcripts.jsonl"

_LOG_PATH_ENV = "FRIDAY_TRANSCRIPT_LOG"

_log_path = Path(os.environ.get(_LOG_PATH_ENV, str(DEFAULT_FILE)))
_log_path.parent.mkdir(parents=True, exist_ok=True)

_q: "queue.Queue[dict | object]" = queue.Queue()
_STOP = object()

# MongoDB integration setup
USE_MONGODB = os.getenv("USE_MONGODB", "true").lower() == "true"
_current_session_id = None

try:
    if USE_MONGODB:
        from db_config import TranscriptDB, ConversationDB
        MONGODB_AVAILABLE = True
        logging.info("MongoDB integration enabled for transcript logging")
    else:
        MONGODB_AVAILABLE = False
        logging.info("MongoDB integration disabled - using file storage")
except ImportError as e:
    MONGODB_AVAILABLE = False
    logging.warning(f"MongoDB not available for transcript logging, using file storage fallback: {e}")


def _worker() -> None:
    while True:
        item = _q.get()
        if item is _STOP:
            break
        try:
            # Try MongoDB first if available
            if MONGODB_AVAILABLE and isinstance(item, dict):
                try:
                    TranscriptDB.log_event(item, _current_session_id)
                except Exception as e:
                    logging.warning(f"Failed to log to MongoDB: {e}")
            
            # Always log to file as backup
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception:
            # swallow errors to avoid crashing host process
            pass
        _q.task_done()


_worker_thread = threading.Thread(target=_worker, daemon=True)
_worker_thread.start()


def log_user_message(content: str, source: Optional[str] = None, meta: Optional[dict] = None) -> None:
    if not content:
        return
    event = {
        "role": "user",
        "content": content,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": source or "agent",
    }
    if meta:
        event["meta"] = meta
    try:
        _q.put_nowait(event)
    except Exception:
        # fallback synchronous write
        try:
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass


def log_event(event: dict) -> None:
    try:
        _q.put_nowait(event)
    except Exception:
        try:
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass


def flush_and_stop(timeout: float = 2.0) -> None:
    try:
        _q.put(_STOP)
        _worker_thread.join(timeout=timeout)
    except Exception:
        pass


def get_log_path() -> str:
    return str(_log_path)

def set_session_id(session_id: str) -> None:
    """Set the current session ID for transcript logging"""
    global _current_session_id
    _current_session_id = session_id
    logging.info(f"Transcript logging session ID set to: {session_id}")

def get_session_id() -> Optional[str]:
    """Get the current session ID"""
    return _current_session_id

def generate_session_id() -> str:
    """Generate a new unique session ID"""
    session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    set_session_id(session_id)
    return session_id

def save_conversation_session(items: list, metadata: Optional[dict] = None) -> Optional[str]:
    """Save complete conversation session to MongoDB and/or file"""
    if not items:
        return None
    
    session_id = _current_session_id or generate_session_id()
    
    # Calculate session metrics
    start_time = None
    end_time = None
    
    for item in items:
        if isinstance(item, dict) and "timestamp" in item:
            timestamp = item["timestamp"]
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except:
                    continue
            
            if start_time is None or timestamp < start_time:
                start_time = timestamp
            if end_time is None or timestamp > end_time:
                end_time = timestamp
    
    # Prepare session data
    session_data = {
        "session_id": session_id,
        "start_time": start_time or datetime.utcnow(),
        "end_time": end_time or datetime.utcnow(),
        "items": items,
        "total_items": len(items),
        "duration_seconds": ((end_time - start_time).total_seconds() if start_time and end_time else 0),
        "lead_generated": any(item.get("type") == "function_call" and item.get("name") == "create_lead" for item in items if isinstance(item, dict)),
        "metadata": metadata or {}
    }
    
    # Try MongoDB first
    if MONGODB_AVAILABLE:
        try:
            mongo_id = ConversationDB.create_session(session_data)
            if mongo_id:
                logging.info(f"Conversation session saved to MongoDB: {mongo_id}")
        except Exception as e:
            logging.error(f"Failed to save session to MongoDB: {e}")
    
    # Always save to file as backup
    try:
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S.%f")
        session_file = DEFAULT_DIR / f"transcript_session_{timestamp}.json"
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
        
        logging.info(f"Conversation session saved to file: {session_file}")
        return str(session_file)
        
    except Exception as e:
        logging.error(f"Failed to save session to file: {e}")
        return None
