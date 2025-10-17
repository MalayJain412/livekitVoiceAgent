"""
LiveKit Webhook Handler for Dynamic Persona Loading

This service listens for LiveKit participant_joined events, extracts the dialed phone number,
fetches the authoritative persona configuration from the CRM API, and dispatches the agent
with the full configuration as metadata.

Architecture:
1. Receives webhook from LiveKit when SIP participant joins
2. Extracts dialed number from sip.trunkPhoneNumber
3. Calls https://devcrm.xeny.ai/apis/api/public/mobile/<dialed_number>
4. Dispatches agent to room with full config as metadata
"""

import os
import json
import logging
from logging_config import configure_logging
import requests
import time
from typing import Optional, Dict, Any
from flask import Flask, request, Response

# LiveKit imports - adjust based on your SDK version
try:
    from livekit import api
    from livekit.api import LiveKitAPI, CreateAgentDispatchRequest
    LIVEKIT_SDK_AVAILABLE = True
except ImportError:
    LIVEKIT_SDK_AVAILABLE = False
    logging.warning("LiveKit SDK not available - will use HTTP API directly")

# Configuration from environment
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
PERSONA_API_BASE = os.getenv("PERSONA_API_BASE", "https://devcrm.xeny.ai/apis/api/public/mobile")
AGENT_TO_DISPATCH = os.getenv("AGENT_TO_DISPATCH", "friday-ai-agent")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # Optional webhook validation

# Initialize Flask app and LiveKit client
app = Flask(__name__)
# Centralized logging config
try:
    configure_logging()
except Exception:
    # Fallback to basicConfig if centralized config fails for any reason
    logging.basicConfig(level=logging.INFO)

if LIVEKIT_SDK_AVAILABLE and LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET:
    try:
        lkapi = LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        logging.info("LiveKit API client initialized")
    except Exception as e:
        logging.error(f"Failed to initialize LiveKit API client: {e}")
        lkapi = None
else:
    lkapi = None
    logging.warning("LiveKit API client not available - check environment variables")


def load_config_for_dialed_number(dialed_number: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """
    Fetch the authoritative persona configuration from the CRM API.
    
    Args:
        dialed_number: The phone number that was dialed (without + prefix)
        timeout: Request timeout in seconds
        
    Returns:
        Complete JSON configuration or None if fetch fails
    """
    if not dialed_number:
        return None
    
    try:
        url = f"{PERSONA_API_BASE}/{dialed_number}"
        logging.info(f"Fetching persona config from: {url}")
        
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        
        config = resp.json()
        logging.info(f"Successfully loaded config for {dialed_number}: {config.get('mobileNo', 'unknown')}")
        return config
        
    except requests.exceptions.Timeout:
        logging.error(f"Timeout fetching config for {dialed_number}")
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error fetching config for {dialed_number}: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response for {dialed_number}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching config for {dialed_number}: {e}")
    
    return None


def dispatch_agent_to_room(room_name: str, metadata: str) -> bool:
    """
    Dispatch the agent to the specified room with configuration metadata.
    
    Args:
        room_name: LiveKit room name
        metadata: JSON string containing persona configuration
        
    Returns:
        True if dispatch successful, False otherwise
    """
    if not lkapi:
        logging.error("LiveKit API client not available")
        return False
    
    try:
        # Create agent dispatch request
        request_obj = CreateAgentDispatchRequest(
            agent_name=AGENT_TO_DISPATCH,
            room=room_name,
            metadata=metadata
        )
        
        # Dispatch the agent
        response = lkapi.agent.create_dispatch(request_obj)
        logging.info(f"Successfully dispatched agent {AGENT_TO_DISPATCH} to room {room_name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to dispatch agent to room {room_name}: {e}")
        return False


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for load balancers/monitoring."""
    return {"status": "healthy", "timestamp": time.time()}


@app.route("/livekit-webhook", methods=["POST"])
def livekit_webhook():
    """
    Handle LiveKit webhook events, specifically participant_joined for SIP callers.
    
    Expected workflow:
    1. Validate webhook (optional if WEBHOOK_SECRET is set)
    2. Parse participant_joined event
    3. Extract dialed number from sip.trunkPhoneNumber
    4. Fetch persona configuration from CRM API
    5. Dispatch agent with configuration as metadata
    """
    
    # Get request data
    payload = request.get_data()
    headers = request.headers
    
    # Optional webhook validation
    if WEBHOOK_SECRET:
        auth_header = headers.get("Authorization", "")
        # TODO: Implement proper webhook signature validation
        # This is a placeholder - implement according to LiveKit webhook security
        if not auth_header:
            logging.warning("Missing Authorization header for webhook")
            return Response(status=401)
    
    # Parse webhook payload
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in webhook payload: {e}")
        return Response(status=400)
    
    # Only process participant_joined events
    if event.get("event") != "participant_joined":
        return Response(status=200)
    
    # Extract event details
    participant = event.get("participant", {})
    room = event.get("room", {})
    room_name = room.get("name") or room.get("sid")
    
    if not room_name:
        logging.error("No room name found in webhook event")
        return Response(status=400)
    
    # Check if this is a SIP participant
    participant_kind = participant.get("kind")
    if participant_kind != "sip":  # Adjust based on actual LiveKit webhook format
        logging.info(f"Ignoring non-SIP participant in room {room_name}")
        return Response(status=200)
    
    # Extract dialed number from participant attributes
    attributes = participant.get("attributes", {})
    metadata = participant.get("metadata", {})
    
    # Try multiple possible field names for dialed number
    dialed_number = (
        attributes.get("sip.trunkPhoneNumber") or
        attributes.get("sip_trunkPhoneNumber") or 
        attributes.get("trunkPhoneNumber") or
        metadata.get("sip.trunkPhoneNumber") or
        metadata.get("dialedNumber")
    )
    
    if not dialed_number:
        logging.warning(f"No dialed number found in participant attributes for room {room_name}")
        logging.debug(f"Available attributes: {attributes}")
        logging.debug(f"Available metadata: {metadata}")
        # Dispatch agent with empty metadata as fallback
        dispatch_agent_to_room(room_name, "{}")
        return Response(status=200)
    
    # Normalize phone number (remove + prefix)
    api_number = str(dialed_number).lstrip("+")
    logging.info(f"Processing inbound call to {dialed_number} (API: {api_number}) in room {room_name}")
    
    # Fetch authoritative configuration
    start_time = time.time()
    authoritative_config = load_config_for_dialed_number(api_number)
    fetch_duration = time.time() - start_time
    
    # Prepare metadata for agent
    if authoritative_config:
        metadata_str = json.dumps(authoritative_config)
        logging.info(f"Config loaded in {fetch_duration:.2f}s for {api_number}")
        
        # Log config summary
        try:
            campaigns = authoritative_config.get("campaigns", [])
            if campaigns:
                persona = campaigns[0].get("voiceAgents", [{}])[0].get("persona", {})
                persona_name = persona.get("name", "unknown")
                logging.info(f"Loaded persona: {persona_name}")
        except (IndexError, KeyError):
            pass
    else:
        metadata_str = "{}"
        logging.warning(f"Using default config for {api_number} (fetch failed in {fetch_duration:.2f}s)")
    
    # Dispatch agent with configuration
    success = dispatch_agent_to_room(room_name, metadata_str)
    
    if success:
        logging.info(f"Webhook processing complete for room {room_name}")
        return Response(status=200)
    else:
        logging.error(f"Failed to dispatch agent for room {room_name}")
        return Response(status=500)


@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler to prevent webhook failures from crashing."""
    logging.error(f"Unhandled exception in webhook handler: {e}", exc_info=True)
    return Response(status=500)


if __name__ == "__main__":
    # Validate required environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    port = int(os.getenv("PORT", 8080))
    logging.info(f"Starting webhook handler on port {port}")
    logging.info(f"Persona API base: {PERSONA_API_BASE}")
    logging.info(f"Agent to dispatch: {AGENT_TO_DISPATCH}")
    
    app.run(host="0.0.0.0", port=port, debug=False)