"""
LiveKit Webhook Handler for Dynamic Persona Loading

Handles participant_joined webhooks, extracts dialed number, fetches CRM config,
and dispatches the 'friday-assistant' agent with the config.
"""

import os
import json
import logging
from logging_config import configure_logging # Assuming this exists
import requests
import time
from datetime import timedelta, datetime # <-- ADDED IMPORT
from typing import Optional, Dict, Any
from flask import Flask, request, Response
from livekit.api import AccessToken, VideoGrants # <-- CORRECTED IMPORT (plural)

# --- Load environment variables first ---
from dotenv import load_dotenv
load_dotenv() # Reads .env file from the current working directory
# ----------------------------------------

# --- CORRECTED IMPORT BLOCK ---
try:
    # Import both AccessToken and VideoGrants (plural) from livekit.api
    LIVEKIT_SDK_AVAILABLE = True
except ImportError as e:
    LIVEKIT_SDK_AVAILABLE = False
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"CRITICAL: Failed to import AccessToken or VideoGrants from livekit.api: {e}", exc_info=True)
    logging.critical("Ensure 'livekit-api' is installed: pip install livekit-api")
    exit("Exiting due to missing LiveKit SDK components.")
# --- END CORRECTED IMPORT BLOCK ---


# Configuration from environment (now read *after* load_dotenv)
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
PERSONA_API_BASE = os.getenv("PERSONA_API_BASE")
if not PERSONA_API_BASE:
     logging.basicConfig(level=logging.CRITICAL)
     logging.critical("CRITICAL ERROR: Environment variable 'PERSONA_API_BASE' is not set.")
     exit("Exiting due to missing PERSONA_API_BASE configuration.")
AGENT_TO_DISPATCH = os.getenv("AGENT_TO_DISPATCH", "friday-assistant")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# Initialize Flask app
app = Flask(__name__)

# Centralized logging config
try:
    configure_logging()
    logging.info("Successfully configured logging using logging_config.")
except NameError:
     logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
     logging.warning("logging_config.py not found or configure_logging() failed, using basicConfig.")
except Exception as e:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.warning(f"Error configuring logging: {e}, using basicConfig.")


# --- Async client block is removed ---

def extract_number_from_sip_uri(uri_string):
    """Extract phone number from SIP URI formats, preserving leading '+'."""
    if not uri_string: return None
    uri_string = str(uri_string).strip().strip('<>')
    if uri_string.startswith('sip:'):
        user_part = uri_string[4:].split('@')[0]
        cleaned_user = user_part.replace('-', '').replace(' ', '')
        if cleaned_user.startswith('+') and cleaned_user[1:].isdigit(): return cleaned_user
        if cleaned_user.isdigit(): return cleaned_user
        logging.debug(f"Returning original SIP user part: {user_part}")
        return user_part
    cleaned = uri_string.replace('-', '').replace(' ', '')
    if cleaned.startswith('+') and cleaned[1:].isdigit(): return cleaned
    if cleaned.isdigit():
        if uri_string.strip().startswith('+'): return uri_string.strip()
        return cleaned
    logging.warning(f"Could not extract a valid number from non-SIP URI string: {uri_string}")
    return None

def load_config_for_dialed_number(dialed_number: str, timeout: int = 10) -> Optional[Dict]:
    """Fetch persona configuration from the CRM API."""
    if not dialed_number:
        logging.warning("load_config_for_dialed_number called with empty number.")
        return None
    api_call_number = str(dialed_number)
    try:
        url = f"{PERSONA_API_BASE}/{api_call_number}"
        logging.info(f"Fetching persona config from: {url}")
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        if 'application/json' not in resp.headers.get('Content-Type', ''):
             logging.error(f"API response for {api_call_number} not JSON. Type: {resp.headers.get('Content-Type')}")
             logging.error(f"Response text (first 500 chars): {resp.text[:500]}")
             return None
        config = resp.json()
        if not isinstance(config, dict):
             logging.error(f"API response for {api_call_number} JSON but not dict: {type(config)}")
             return None
        logging.info(f"Successfully loaded config for {api_call_number}")
        logging.debug(f"Config keys: {list(config.keys())}")
        return config
    except requests.exceptions.Timeout: logging.error(f"Timeout fetching config for {api_call_number} from {url}")
    except requests.exceptions.HTTPError as e: logging.error(f"HTTP error {e.response.status_code} fetching config for {api_call_number} from {url}\nBody: {e.response.text[:500]}")
    except requests.exceptions.RequestException as e: logging.error(f"Network error fetching config for {api_call_number} from {url}: {e}")
    except json.JSONDecodeError as e: logging.error(f"Invalid JSON response for {api_call_number} from {url}: {e}\nText: {resp.text[:500]}")
    except Exception as e: logging.error(f"Unexpected error fetching config for {api_call_number}: {e}", exc_info=True)
    return None


def save_last_called_number(number: str, full_config: Optional[Dict] = None) -> None:
    """Persist the last called number and optional full_config to leads/last_called_number.json

    This file is used as a simple cross-process fallback so other workers (cagent/persona)
    can read the most recent dialed number when job metadata is missing.
    """
    try:
        leads_dir = os.path.join(os.path.dirname(__file__), "leads")
        os.makedirs(leads_dir, exist_ok=True)
        file_path = os.path.join(leads_dir, "last_called_number.json")
        payload = {
            "number": number,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "full_config": full_config or {}
        }
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        # atomic replace
        os.replace(tmp_path, file_path)
        logging.info(f"Saved last called number to {file_path}")
    except Exception as e:
        logging.error(f"Failed to save last called number: {e}", exc_info=True)

def dispatch_agent_to_room(room_name: str, metadata: str) -> bool:
    """Dispatch the agent using a direct synchronous HTTP request."""
    if not LIVEKIT_SDK_AVAILABLE: logging.error("LiveKit SDK components missing. Cannot dispatch.") ; return False
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]): logging.error("LiveKit env vars missing. Cannot dispatch.") ; return False

    try: # Generate Token
        token_builder = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token_builder.identity = "friday-webhook-handler"
        # Use timedelta for ttl
        token_builder.ttl = timedelta(seconds=60) # <-- CORRECTED TTL
        grant = VideoGrants(agent=True)
        token_builder.with_grants(grant)
        token = token_builder.to_jwt()
    except Exception as e: logging.error(f"Failed to generate LiveKit auth token: {e}", exc_info=True) ; return False

    http_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
    if not http_url.startswith(("http://", "https://")): logging.error(f"Invalid LIVEKIT_URL for HTTP: '{LIVEKIT_URL}'") ; return False
    api_endpoint = f"{http_url}/twirp/livekit.AgentService/CreateAgentDispatch"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"agent_name": AGENT_TO_DISPATCH, "room": room_name, "metadata": metadata}

    try: # Make API Call
        logging.info(f"Dispatching Agent: '{AGENT_TO_DISPATCH}', Room: '{room_name}', Endpoint: '{api_endpoint}'")
        logging.debug(f"Dispatch metadata preview (first 100 chars): {metadata[:100]}...")
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        try: logging.debug(f"Dispatch API success response: {response.json()}")
        except json.JSONDecodeError: logging.debug("Dispatch API success response not JSON.")
        logging.info(f"Successfully dispatched agent '{AGENT_TO_DISPATCH}' to room '{room_name}'")
        return True
    except requests.exceptions.Timeout: logging.error(f"Timeout dispatching agent to room '{room_name}'")
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP request failed during agent dispatch: {e}")
        if e.response is not None:
            logging.error(f"Dispatch failed - Status: {e.response.status_code}")
            try: error_details = e.response.json() ; msg = error_details.get('msg', json.dumps(error_details)) ; logging.error(f"Dispatch failed - API Error: {msg}")
            except json.JSONDecodeError: logging.error(f"Dispatch failed - Response (non-JSON): {e.response.text[:500]}")
    except Exception as e: logging.error(f"Unexpected error during agent dispatch: {e}", exc_info=True)
    return False


@app.route("/livekit-webhook", methods=["POST"])
def livekit_webhook():
    """Handle LiveKit participant_joined webhook for SIP callers."""
    if WEBHOOK_SECRET: # Basic auth check
        auth_header = request.headers.get("Authorization")
        if not auth_header: logging.warning("Missing Auth header with WEBHOOK_SECRET set.") #; return Response("Unauthorized", status=401)

    try: payload = request.get_data(); event = json.loads(payload)
    except Exception as e: logging.error(f"Webhook payload error: {e}") ; return Response("Bad Request", status=400)

    event_type = event.get("event")
    logging.debug(f"Received webhook event: {event_type}")
    if event_type != "participant_joined": return Response(status=200) # OK for ignored events

    participant = event.get("participant", {})
    room = event.get("room", {})
    room_name = room.get("name") or room.get("sid")
    if not room_name: logging.error("Webhook Error: Missing room name/SID.") ; return Response("Bad Request", status=400)

    participant_kind = participant.get("kind")
    participant_identity = participant.get("identity")
    logging.info(f"Processing participant_joined: Id='{participant_identity}', Kind='{participant_kind}', Room='{room_name}'")
    logging.debug(f"Full participant object: {json.dumps(participant, indent=2)}")

    if participant_kind is None or participant_kind.lower() != "sip":
        logging.info(f"Ignoring non-SIP participant (Kind was '{participant_kind}')")
        return Response(status=200)

    attributes = participant.get("attributes") or {}
    dialed_number, extraction_source = None, "None"
    preferred_sources = [
        ("attributes.dialedNumber", attributes.get("dialedNumber")), ("attributes.calledNumber", attributes.get("calledNumber")),
        ("attributes.sip.calledNumber", attributes.get("sip.calledNumber")), ("attributes.toUser", attributes.get("toUser")),
        ("attributes.sip.toUser", attributes.get("sip.toUser")), ("attributes.sip.requestURI", attributes.get("sip.requestURI")),
        ("attributes.sip.toHeader", attributes.get("sip.toHeader")),
    ]
    for source, value in preferred_sources:
        if value:
            extracted = extract_number_from_sip_uri(value)
            if extracted: dialed_number, extraction_source = extracted, source ; logging.info(f"Extracted dialed number '{dialed_number}' from {source}") ; break

    if not dialed_number and room_name: # Fallback: Room name pattern
         prefixes = ["friday-call-", "room-", "call-", "sip-"]
         for prefix in prefixes:
              if room_name.startswith(prefix):
                   potential_num_part = room_name[len(prefix):].lstrip('_').split('_')[0]
                   extracted = extract_number_from_sip_uri(potential_num_part)
                   if extracted: dialed_number, extraction_source = extracted, f"room name pattern '{prefix}'" ; logging.info(f"Extracted dialed number '{dialed_number}' from {extraction_source}") ; break

    if not dialed_number:
        logging.warning(f"Could not extract dialed number for room '{room_name}'. Dispatching agent with empty config.")
        logging.debug(f"Attributes: {json.dumps(attributes, indent=2)}")
        dispatch_agent_to_room(room_name, "{}") ; return Response(status=200)

    logging.info(f"Using dialed number '{dialed_number}' (Source: {extraction_source})")
    api_number = str(dialed_number).strip()
    logging.info(f"Processing call using API number='{api_number}' for room='{room_name}'")

    start_time = time.time() ; authoritative_config = load_config_for_dialed_number(api_number) ; fetch_duration = time.time() - start_time
    logging.info(f"CRM API fetch took {fetch_duration:.3f}s for number '{api_number}'")

    metadata_str = "{}"
    if authoritative_config and isinstance(authoritative_config, dict):
        try: metadata_str = json.dumps(authoritative_config) ; logging.info(f"Loaded config for {api_number}")
        except TypeError as e: logging.error(f"JSON serialization error for {api_number}: {e}", exc_info=True)
    elif authoritative_config is None: logging.warning(f"CRM fetch failed for {api_number}. Using empty config.")
    else: logging.error(f"CRM returned non-dict for {api_number}: {type(authoritative_config)}. Using empty config.")

    success = dispatch_agent_to_room(room_name, metadata_str)
    if success: logging.info(f"Webhook success: Agent dispatched to room '{room_name}'.") ; return Response(status=200)
    else: logging.error(f"Webhook failed: Agent dispatch failed for room '{room_name}'.") ; return Response("Agent dispatch failed", status=500)

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler."""
    logging.error(f"Unhandled exception in webhook handler: {e}", exc_info=True)
    return Response("Internal Server Error", status=500)

if __name__ == "__main__":
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "PERSONA_API_BASE"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing: logging.critical(f"CRITICAL ERROR: Missing env vars: {missing}. Check .env file.") ; exit(1)
    if not LIVEKIT_SDK_AVAILABLE: logging.critical("CRITICAL ERROR: Failed to import LiveKit SDK components. Ensure 'livekit-api' is installed.") ; exit(1)

    port = int(os.getenv("PORT", 8080))
    logging.info(f"Starting Friday AI Webhook Handler on http://0.0.0.0:{port}")
    logging.info(f"LiveKit URL: {LIVEKIT_URL}")
    logging.info(f"Persona API Base URL: {PERSONA_API_BASE}")
    logging.info(f"Agent to Dispatch: {AGENT_TO_DISPATCH}")
    app.run(host="0.0.0.0", port=port, debug=False)