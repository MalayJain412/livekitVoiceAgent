import requests
import json 

API_KEY = ""
URL = "https://api.elevenlabs.io/v1/voices"

headers = {
  "Accept": "application/json",
  "xi-api-key": API_KEY
}

try:
    response = requests.get(URL, headers=headers)
    response.raise_for_status() # Check for HTTP errors

    data = response.json()

    print(f"--- Found {len(data['voices'])} voices ---")
    for voice in data['voices']:
        print(f"- Name: {voice['name']}, ID: {voice['voice_id']}")

    # Uncomment the line below to see the full, messy JSON output
    # print(json.dumps(data, indent=2))

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")