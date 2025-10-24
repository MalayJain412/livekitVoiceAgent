import requests
import json

# --- Configuration ---
API_KEY = "YOUR_ELEVENLABS_API_KEY"

# This is the "Clyde" voice ID you were testing
VOICE_ID = "2EiwWnXFnvU5JabPnv8n" 

TEXT_TO_SAY = "Hello, this is a test using the raw requests method."
OUTPUT_FILENAME = "clyde_test.mp3"
# --- End Configuration ---

URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

headers = {
  "Accept": "audio/mpeg",
  "xi-api-key": API_KEY,
  "Content-Type": "application/json"
}

data = {
  "text": TEXT_TO_SAY,
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
  }
}

try:
    print(f"Generating audio for {VOICE_ID} and saving to {OUTPUT_FILENAME}...")
    response = requests.post(URL, json=data, headers=headers)
    response.raise_for_status() # Check for HTTP errors

    # Save the received audio content to a file
    with open(OUTPUT_FILENAME, 'wb') as f:
        f.write(response.content)
        
    print(f"\nSuccess! Audio saved to {OUTPUT_FILENAME}")
    print(f"You can now open '{OUTPUT_FILENAME}' to listen to the voice.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")