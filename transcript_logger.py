import os
import json
import threading
import queue
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


def _worker() -> None:
    while True:
        item = _q.get()
        if item is _STOP:
            break
        try:
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
