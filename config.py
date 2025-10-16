import os
import datetime

_conversation_log_path = None

# =============================================================================
# LIVEKIT CONFIGURATION
# =============================================================================
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

# =============================================================================
# AI MODEL CONFIGURATION
# =============================================================================

# --- CURRENTLY ACTIVE: Azure OpenAI Configuration ---
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_LLM_DEPLOYMENT = os.environ.get("AZURE_OPENAI_LLM_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_STT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_STT_DEPLOYMENT", "gpt-4o-transcribe")
# Alternative STT configuration (if using different endpoint for STT)
AZURE_OPENAI_STT_API_KEY = os.environ.get("AZURE_OPENAI_STT_API_KEY", AZURE_OPENAI_API_KEY)
AZURE_OPENAI_STT_ENDPOINT = os.environ.get("AZURE_OPENAI_STT_ENDPOINT", AZURE_OPENAI_ENDPOINT)
AZURE_OPENAI_STT_API_VERSION = os.environ.get("AZURE_OPENAI_STT_API_VERSION", OPENAI_API_VERSION)

# --- CURRENTLY ACTIVE: Cartesia TTS Configuration ---
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")

# --- NOT CURRENTLY USED: OpenAI Configuration ---
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- NOT CURRENTLY USED: Google/Gemini Configuration ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
# GOOGLE_API_KEY_1 = os.environ.get("GOOGLE_API_KEY_1")
# GOOGLE_API_KEY_2 = os.environ.get("GOOGLE_API_KEY_2")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")

# --- NOT CURRENTLY USED: Deepgram STT Configuration ---
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "friday_ai")
MONGODB_TIMEOUT = os.environ.get("MONGODB_TIMEOUT", "10000")
USE_MONGODB = os.environ.get("USE_MONGODB", "true").lower() == "true"

# =============================================================================
# OTHER CONFIGURATION
# =============================================================================
SECRET_KEY = os.environ.get("SECRET_KEY")

# --- NOT CURRENTLY USED: Gmail Configuration ---
# GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
# GMAIL_USER = os.environ.get("GMAIL_USER")

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