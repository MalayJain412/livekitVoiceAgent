"""
AI Service Instances Configuration
Centralized configuration for STT, LLM, and TTS instances
"""
import json
import os
from typing import Optional, Dict
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
    AZURE_OPENAI_TTS_API_KEY,
    AZURE_OPENAI_TTS_ENDPOINT,
    AZURE_OPENAI_TTS_API_VERSION,
    AZURE_OPENAI_TTS_DEPLOYMENT,
    CARTESIA_API_KEY,
    LLM_MODEL,
    DEEPGRAM_API_KEY
)

# --- NEW: Helper functions for voice mapping and payload parsing ---

def load_voice_data(filepath='./voices/all_voices.json'):
    """Loads the voice data from the JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Voice data file not found at {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return {}

def find_voice_id(provider, name, all_voices):
    """
    Finds the specific voice ID for a given provider and voice name.
    Handles different structures within the all_voices.json file.
    """
    provider_key = provider.lower()
    
    if provider_key not in all_voices:
        print(f"Warning: Provider '{provider_key}' not found in voice data.")
        return name # Fallback to the name if provider is not in our mapping

    voices_data = all_voices[provider_key]

    if provider_key == "cartesia":
        # Cartesia has language-specific lists
        for lang_voices in voices_data.values():
            for voice in lang_voices:
                if voice.get("name") == name:
                    return voice.get("id")
    elif provider_key == "elevenlabs":
        # ElevenLabs has a 'speakers' list and names can be complex
        for speaker in voices_data.get("speakers", []):
            # Check if the simple name (e.g., "Priyanka") is at the start of the full name
            if speaker.get("name", "").startswith(name):
                return speaker.get("id")
    # For Sarvam and OpenAI (which is actually Azure OpenAI), the name is the identifier
    elif provider_key in ["sarvam", "openai", "azure"]:
        # These providers use the name directly, so we just return it.
        # This check confirms the name exists in our list.
        # Note: "openai" refers to Azure OpenAI in our system
        key_map = {"sarvam": "speakers", "openai": "openai_voices", "azure": "openai_voices"}
        voice_list_key = key_map[provider_key]
        for voice in voices_data.get(voice_list_key, []):
            # Case-insensitive comparison for Sarvam
            if voice.get("name", "").lower() == name.lower():
                return voice.get("name") # Return the correct case from our data
    
    # Special fallback for Sarvam - if voice not found, use a default
    if provider_key == "sarvam":
        print(f"Warning: Voice '{name}' not found for Sarvam. Falling back to 'anushka'.")
        return "anushka"  # Safe fallback that exists in Sarvam
    
    print(f"Warning: Voice '{name}' not found for provider '{provider}'. Using name as fallback.")
    return name # Fallback if no ID is found

def extract_voice_details(payload):
    """
    Safely extracts voice details (model, name, language) from the API payload.
    Returns None if the structure is not as expected.
    """
    try:
        # Navigate through the nested structure
        voice_details = payload["campaigns"][0]["voiceAgents"][0]["voiceDetails"]
        provider = voice_details.get("voiceModel")
        voice_name = voice_details.get("name")
        language_code = voice_details.get("language", "en").lower() # Default to 'en'
        
        print(f"Extracted voice details: provider={provider}, name={voice_name}, language={language_code}")
        
        # Simple language code mapping
        lang_map = {
            "english": "en", "hindi": "hi", "en": "en", "hi": "hi"
        }
        language = lang_map.get(language_code.lower(), "en")

        if provider and voice_name:
            return provider, voice_name, language
    except (KeyError, IndexError, TypeError) as e:
        # Handle cases where keys are missing or payload isn't a list/dict
        print(f"Error: Could not extract voice details from payload: {e}")
    return None, None, None


# --- MODIFIED: Core instance creation functions ---

def get_llm_instance(provider="google"): # Added default for simplicity
    """Get LLM instance based on provider"""
    if provider == "azure":
        return openai.LLM.with_azure(
            model="gpt-4o-mini",
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


def get_stt_instance(provider="deepgram"): # Added default for simplicity
    """Get STT instance based on provider"""
    if provider == "azure":
        return openai.STT.with_azure(
            model="AZURE_OPENAI_STT_DEPLOYMENT",
            azure_endpoint=AZURE_OPENAI_STT_ENDPOINT,
            api_key=AZURE_OPENAI_STT_API_KEY,
            azure_deployment=AZURE_OPENAI_STT_DEPLOYMENT,
            api_version=AZURE_OPENAI_STT_API_VERSION,
            language="multi"
        )
    elif provider == "deepgram":
        return deepgram.STT(
            model="nova-3-general",  # Use stable nova-3 model
            language="multi",  # Multi-language support for Hindi-English
            smart_format=True,  # Enable smart formatting for better readability
            punctuate=True,  # Enable punctuation
            interim_results=True  # Enable interim results for better UX
        )
    else:
        raise ValueError(f"Unsupported STT provider: {provider}")

# MODIFIED get_tts_instance to be fully dynamic
def get_tts_instance(provider, voice_identifier, language):
    """
    Get TTS instance based on provider, voice ID/name, and language.
    Note: 'openai' provider refers to Azure OpenAI, not standard OpenAI
    """
    provider_lower = provider.lower()
    print(f"Configuring TTS for provider: {provider_lower}, voice: {voice_identifier}, lang: {language}")

    if provider_lower == "cartesia":
        return cartesia.TTS(
            model="sonic-2",
            language=language,
            voice=voice_identifier, # Use the looked-up ID
            api_key=CARTESIA_API_KEY,
        )
    elif provider_lower == "elevenlabs":
        return elevenlabs.TTS(
            voice_id=voice_identifier, # Use the looked-up ID
            model="eleven_multilingual_v2"
        )
    elif provider_lower == "sarvam":
        # Ensure the voice name is lowercase as Sarvam expects
        speaker_name = voice_identifier.lower()
        print(f"Using Sarvam speaker: {speaker_name}")
        return sarvam.TTS(
            target_language_code=f"{language}-IN",
            speaker=speaker_name, # Sarvam uses lowercase names
            pace=0.8
        )
    elif provider_lower in ["openai", "azure"]:
        # When users specify "openai", they mean Azure OpenAI (not standard OpenAI)
        # Azure OpenAI TTS using the unified realtime resource
        return openai.TTS.with_azure(
            model=AZURE_OPENAI_TTS_DEPLOYMENT,  # TTS model for Azure OpenAI
            voice=voice_identifier.lower(),
            azure_endpoint=AZURE_OPENAI_TTS_ENDPOINT,
            api_key=AZURE_OPENAI_TTS_API_KEY,
            azure_deployment=AZURE_OPENAI_TTS_DEPLOYMENT,
            api_version=AZURE_OPENAI_TTS_API_VERSION
        )
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}")


def get_vad_instance():
    """Get Voice Activity Detection instance - using basic silero for local setup"""
    # Note: For local LiveKit setup, advanced VAD features may not be available
    # Using basic silero configuration without cloud-specific features
    return silero.VAD.load()


# --- NEW: Main function to use with your application ---

def get_instances_from_payload(payload):
    """
    Get all configured AI service instances based on the API payload.
    Falls back to defaults if payload parsing fails.
    """
    all_voices = load_voice_data() # Load the voice mappings

    # Extract TTS details from payload
    tts_provider, tts_voice_name, tts_language = extract_voice_details(payload)
    
    if tts_provider and tts_voice_name and all_voices:
        # Find the specific voice ID or name required by the SDK
        voice_identifier = find_voice_id(tts_provider, tts_voice_name, all_voices)
        try:
            tts_instance = get_tts_instance(tts_provider, voice_identifier, tts_language)
        except Exception as e:
            print(f"Error creating TTS instance for {tts_provider} with voice {tts_voice_name}: {e}")
            print("Falling back to default TTS configuration.")
            # Fallback to a reliable default
            tts_instance = get_tts_instance("cartesia", "faf0731e-dfb9-4cfc-8119-259a79b27e12", "hi")
    else:
        # Fallback to a default if payload is invalid or voice data is missing
        print("Falling back to default TTS configuration.")
        tts_instance = get_tts_instance("cartesia", "faf0731e-dfb9-4cfc-8119-259a79b27e12", "hi")

    return {
        "llm": get_llm_instance("azure"),     # Use Azure OpenAI for LLM
        "stt": get_stt_instance("deepgram"),     # Use Deepgram for STT  
        "tts": tts_instance,                  # Dynamically configured
        "vad": get_vad_instance()
    }


def load_test_payload() -> Optional[Dict]:
    """
    Load test payload from local file for testing instance creation logic.
    Used when TEST_API_RESPONSE_FILE is set.
    """
    test_file = os.getenv("TEST_API_RESPONSE_FILE")
    if test_file:
        try:
            print(f"TEST MODE: Loading test payload from local file: {test_file}")
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Successfully loaded test payload from {test_file}")
            return data
        except Exception as e:
            print(f"Failed to load test payload from {test_file}: {e}")
            return None
    return None   