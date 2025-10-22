"""
CRM Upload Module
Handles uploading call data (transcription and lead) to CRM API
"""

import logging
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

# API endpoint
CRM_UPLOAD_URL = "https://devcrm.xeny.ai/apis/api/public/upload"

def upload_call_data(
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    call_details: Dict[str, Any],
    caller: Dict[str, str],
    transcription: Dict[str, Any],
    lead: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Upload call data to CRM API.

    Args:
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID
        client_id: Client ID
        call_details: Call details dict containing callId, direction, startTime, endTime, etc.
        caller: Caller info dict containing phoneNumber
        transcription: Transcription data
        lead: Lead data (optional)

    Returns:
        bool: True if upload successful, False otherwise
    """

    payload = {
        "campaignId": campaign_id,
        "voiceAgentId": voice_agent_id,
        "client": client_id,
        "callDetails": call_details,
        "caller": caller,
        "transcription": transcription,
        "lead": lead or {}
    }

    try:
        logging.info(f"Uploading call data for callId: {call_details.get('callId', 'unknown')}")

        response = requests.post(
            CRM_UPLOAD_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        logging.info(f"Successfully uploaded call data to CRM. Response: {response.status_code}")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to upload call data to CRM: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error uploading call data: {e}")
        return False

def create_call_details(
    call_id: str,
    direction: str,
    start_time: datetime,
    end_time: datetime,
    status: str,
    recording_url: Optional[str] = None,
    recording_duration: Optional[int] = None,
    recording_size: Optional[int] = None,
    caller_number: str = ""
) -> Dict[str, Any]:
    """
    Helper function to create call details dict.

    Args:
        call_id: Unique call identifier
        direction: Call direction (inbound/outbound)
        start_time: Call start datetime
        end_time: Call end datetime
        status: Call status (completed, failed, etc.)
        recording_url: URL to call recording
        recording_duration: Recording duration in seconds
        recording_size: Recording file size in bytes
        caller_number: Caller's phone number

    Returns:
        Dict containing call details
    """

    duration = int((end_time - start_time).total_seconds())

    call_details = {
        "callId": call_id,
        "direction": direction,
        "startTime": start_time.isoformat() + "Z",
        "endTime": end_time.isoformat() + "Z",
        "duration": duration,
        "status": status,
        "callerNumber": caller_number
    }

    if recording_url:
        call_details["recordingUrl"] = recording_url
    if recording_duration:
        call_details["recordingDuration"] = recording_duration
    if recording_size:
        call_details["recordingSize"] = recording_size

    return call_details