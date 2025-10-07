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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"conversation_{timestamp}.json")
    set_conversation_log_path(log_path)
    
    # Initialize empty conversation file
    import json
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"conversation": []}, f, ensure_ascii=False, indent=2)
    
    return log_path