import os
import datetime

_conversation_log_path = None

def set_conversation_log_path(path: str):
    global _conversation_log_path
    _conversation_log_path = path

def get_conversation_log_path() -> str:
    if _conversation_log_path is None:
        raise RuntimeError("Conversation log path not set!")
    return _conversation_log_path

def setup_conversation_log():
    """Setup conversation log file path and create directory if needed"""
    log_dir = os.path.join(os.getcwd(), "conversations")
    os.makedirs(log_dir, exist_ok=True)
    # Keep behavior minimal: ensure directory exists and return directory path.
    return log_dir