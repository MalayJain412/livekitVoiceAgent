import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get from your environment variables (safer than hardcoding)
ENDPOINT = os.getenv("AZURE_OPENAI_TTS_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_TTS_API_KEY")

if not API_KEY:
    print("Error: AZURE_OPENAI_TTS_API_KEY environment variable is not set")
    print("Please add it to your .env file:")
    print("AZURE_OPENAI_TTS_API_KEY=your_api_key_here")
    exit(1)

print("=== Testing Azure OpenAI TTS Connection ===")
print(f"Endpoint: {ENDPOINT}")

# For Azure OpenAI, we can't list deployments directly via API
# Instead, let's test the TTS endpoint directly and show available voices

# Standard OpenAI TTS voices that work with Azure OpenAI
OPENAI_TTS_VOICES = [
    {"name": "alloy", "description": "Neutral, balanced voice"},
    {"name": "echo", "description": "Male voice, clear and direct"},
    {"name": "fable", "description": "British accent, storytelling voice"},
    {"name": "onyx", "description": "Deep male voice, authoritative"},
    {"name": "nova", "description": "Young female voice, energetic"},
    {"name": "shimmer", "description": "Female voice, soft and gentle"}
]

print("=== Available OpenAI TTS Voices ===")
for i, voice in enumerate(OPENAI_TTS_VOICES, 1):
    print(f"{i}. {voice['name']} - {voice['description']}")

# Test connection by trying to make a simple TTS request
test_url = f"{ENDPOINT.rstrip('/')}/openai/deployments/gpt-4o-mini-tts/audio/speech"
headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

test_data = {
    "model": "tts-1",
    "input": "Hello, this is a test.",
    "voice": "alloy"
}

print("\n=== Testing TTS Endpoint Connection ===")
try:
    # We won't actually send audio data, just test if the endpoint is reachable
    response = requests.post(test_url, headers=headers, json=test_data, params={"api-version": "2024-06-01"})
    
    if response.status_code == 200:
        print("✅ TTS endpoint is working!")
        print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
    elif response.status_code == 401:
        print("❌ Authentication failed - check your API key")
    elif response.status_code == 404:
        print("❌ TTS deployment not found - check your deployment name")
    else:
        print(f"⚠️  Unexpected response: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Connection failed: {e}")

print("\n=== Voice Configuration for instances.py ===")
print("Add this to your voices/openai.json file:")
openai_config = {
    "openai_voices": [
        {"id": f"OA{i:03d}", "name": voice["name"].title(), "description": voice["description"]}
        for i, voice in enumerate(OPENAI_TTS_VOICES, 1)
    ]
}
print(json.dumps(openai_config, indent=2))