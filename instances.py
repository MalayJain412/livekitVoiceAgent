"""
AI Service Instances Configuration
Centralized configuration for STT, LLM, and TTS instances
"""

from livekit.plugins import google, cartesia, openai, deepgram, silero, elevenlabs, sarvam
from config import (
    AZURE_OPENAI_API_KEY, 
    AZURE_OPENAI_ENDPOINT, 
    OPENAI_API_VERSION,
    AZURE_OPENAI_LLM_DEPLOYMENT, 
    AZURE_OPENAI_STT_DEPLOYMENT,
    AZURE_OPENAI_STT_API_KEY, 
    AZURE_OPENAI_STT_ENDPOINT,
    AZURE_OPENAI_STT_API_VERSION,
    CARTESIA_API_KEY,
    LLM_MODEL,
    DEEPGRAM_API_KEY
)


def get_llm_instance(provider):
    """Get LLM instance based on provider"""
    if provider == "azure":
        return openai.LLM.with_azure(
            model=AZURE_OPENAI_LLM_DEPLOYMENT,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            azure_deployment=AZURE_OPENAI_LLM_DEPLOYMENT,
            api_version=OPENAI_API_VERSION,
            temperature=1
        )
    elif provider == "google":
        return google.LLM(model=LLM_MODEL, temperature=0.8)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_stt_instance(provider):
    """Get STT instance based on provider"""
    if provider == "azure":
        return openai.STT.with_azure(
            model=AZURE_OPENAI_STT_DEPLOYMENT,
            azure_endpoint=AZURE_OPENAI_STT_ENDPOINT,
            api_key=AZURE_OPENAI_STT_API_KEY,
            azure_deployment=AZURE_OPENAI_STT_DEPLOYMENT,
            api_version=AZURE_OPENAI_STT_API_VERSION,
            language="multi"
        )
    elif provider == "deepgram":
        return deepgram.STT(
            model="nova-3", 
            language="multi"
        )
    else:
        raise ValueError(f"Unsupported STT provider: {provider}")


def get_tts_instance(provider):
    """Get TTS instance based on provider"""
    if provider == "cartesia":
        return cartesia.TTS(
            model="sonic-2",
            language="hi",
            voice="f91ab3e6-5071-4e15-b016-cde6f2bcd222",
            api_key=CARTESIA_API_KEY,
        )
    elif provider == "elevenlabs":
        return elevenlabs.TTS(
            voice_id="kiaJRdXJzloFWi6AtFBf", # Tarini
            # voice_id="1zUSi8LeHs9M2mV8X6YS",
            model="eleven_multilingual_v2"
        )
    elif provider == "sarvam":
        return sarvam.TTS(
            target_language_code="hi-IN",
            speaker="vidya",
            pace=0.8
        )
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}")


def get_vad_instance():
    """Get Voice Activity Detection instance"""
    return silero.VAD.load()


# Default instances - matching original cagent.py configuration
def get_default_instances():
    """Get default configured instances matching original cagent.py setup"""
    return {
        "llm": get_llm_instance("google"),  # Original used Azure OpenAI
        "stt": get_stt_instance("deepgram"),  # Original used Deepgram
        "tts": get_tts_instance("cartesia"),  # Original used Cartesia
        # "tts": get_tts_instance("sarvam"),
        "vad": get_vad_instance()  # Original used Silero VAD
    }   