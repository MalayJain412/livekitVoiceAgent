import os
import requests
import json

# Configuration — change as needed
# API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")
API_KEY = "AIzaSyAeGYOH50k-ErRaisS60dyIIpqPpgatgwE"
MODEL = "gemini-2.5-flash"  # or whichever model you intend to use
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"  # or correct endpoint
# E.g. URL for “generateContent” for Gemini
ENDPOINT = f"{BASE_URL}/models/{MODEL}:generateContent"

def check_key_has_credits():
    """Makes a minimal test prompt to check if key is valid / has credit."""
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY  # as per Gemini docs :contentReference[oaicite:0]{index=0}
    }
    # A trivial payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hi"
                    }
                ]
            }
        ]
    }
    try:
        resp = requests.post(ENDPOINT, headers=headers, data=json.dumps(payload))
    except Exception as e:
        print("Network / request error:", e)
        return False, f"Request failed: {e}"
    
    # Check status code and response
    if resp.status_code == 200:
        # Key is valid and responded. We *assume* credits are okay.
        return True, "Success — key seems valid"
    else:
        # If you have an error body, inspect it
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        # Common status codes: 400, 403, 429, etc.
        return False, f"Error: status {resp.status_code}, body: {err}"

if __name__ == "__main__":
    ok, msg = check_key_has_credits()
    print("Has credit / valid key?:", ok)
    print("Message:", msg)
