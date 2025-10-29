"""
CRM Upload Module
Handles uploading call data (transcription and lead) to CRM API
"""

import logging
import requests
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# API endpoint
CRM_UPLOAD_URL = "https://devcrm.xeny.ai/apis/api/public/call-data"

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

def convert_transcript_to_api_format(transcript_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert transcript session data to API format.
    
    Args:
        transcript_data: Transcript session data from transcript_logger
        
    Returns:
        Dict containing formatted transcription data for API
    """
    if not transcript_data:
        return {}
    
    # Extract conversation items and format them
    items = transcript_data.get("items", [])
    conversation_items = []
    
    for item in items:
        if isinstance(item, dict) and item.get("role") in ["user", "assistant"]:
            conversation_item = {
                "role": item.get("role"),
                "content": item.get("content", ""),
                "timestamp": item.get("timestamp"),
                "source": item.get("source", "")
            }
            
            # Add additional fields if available
            if "transcript_confidence" in item:
                conversation_item["transcript_confidence"] = item["transcript_confidence"]
            if "interrupted" in item:
                conversation_item["interrupted"] = item["interrupted"]
                
            conversation_items.append(conversation_item)
    
    return {
        "session_id": transcript_data.get("session_id"),
        "start_time": transcript_data.get("start_time"),
        "end_time": transcript_data.get("end_time"),
        "duration_seconds": transcript_data.get("duration_seconds", 0),
        "total_items": len(conversation_items),
        "conversation_items": conversation_items,
        "lead_generated": transcript_data.get("lead_generated", False),
        "metadata": transcript_data.get("metadata", {})
    }

def convert_lead_to_api_format(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert lead data to API format.
    
    Args:
        lead_data: Lead data from Friday AI Assistant
        
    Returns:
        Dict containing formatted lead data for API
    """
    if not lead_data:
        return {}
    
    return {
        "name": lead_data.get("name", ""),
        "email": lead_data.get("email", ""),
        "company": lead_data.get("company", ""),
        "interest": lead_data.get("interest", ""),
        "phone": lead_data.get("phone", ""),
        "job_title": lead_data.get("job_title", ""),
        "budget": lead_data.get("budget", ""),
        "timeline": lead_data.get("timeline", ""),
        "timestamp": lead_data.get("timestamp"),
        "source": lead_data.get("source", "Friday AI Assistant"),
        "status": lead_data.get("status", "new")
    }

def upload_call_data_from_session(
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    call_id: str,
    caller_phone: str,
    direction: str = "inbound",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: str = "completed",
    transcript_data: Optional[Dict[str, Any]] = None,
    lead_data: Optional[Dict[str, Any]] = None,
    recording_url: Optional[str] = None,
    recording_duration: Optional[int] = None,
    recording_size: Optional[int] = None
) -> bool:
    """
    Upload complete call data from a session to CRM API.
    
    Args:
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID
        client_id: Client ID
        call_id: Unique call identifier
        caller_phone: Caller's phone number
        direction: Call direction (inbound/outbound)
        start_time: Call start datetime
        end_time: Call end datetime
        status: Call status
        transcript_data: Complete transcript session data
        lead_data: Lead data if any was generated
        recording_url: URL to call recording
        recording_duration: Recording duration in seconds
        recording_size: Recording file size in bytes
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    
    # Use current time if not provided
    if not start_time:
        start_time = datetime.utcnow()
    if not end_time:
        end_time = datetime.utcnow()
    
    # Create call details
    call_details = create_call_details(
        call_id=call_id,
        direction=direction,
        start_time=start_time,
        end_time=end_time,
        status=status,
        recording_url=recording_url,
        recording_duration=recording_duration,
        recording_size=recording_size,
        caller_number=caller_phone
    )
    
    # Format caller info
    caller = {
        "phoneNumber": caller_phone
    }
    
    # Convert transcript and lead data to API format
    transcription = convert_transcript_to_api_format(transcript_data) if transcript_data else {}
    lead = convert_lead_to_api_format(lead_data) if lead_data else {}
    
    return upload_call_data(
        campaign_id=campaign_id,
        voice_agent_id=voice_agent_id,
        client_id=client_id,
        call_details=call_details,
        caller=caller,
        transcription=transcription,
        lead=lead
    )

def upload_from_transcript_file(
    transcript_file_path: str,
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    caller_phone: str,
    call_id: Optional[str] = None,
    lead_file_path: Optional[str] = None
) -> bool:
    """
    Upload call data from saved transcript and lead files.
    
    Args:
        transcript_file_path: Path to transcript session JSON file
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID
        client_id: Client ID
        caller_phone: Caller's phone number
        call_id: Call ID (auto-generated if not provided)
        lead_file_path: Path to lead JSON file (optional)
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        # Load transcript data
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        # Load lead data if provided
        lead_data = None
        if lead_file_path and os.path.exists(lead_file_path):
            with open(lead_file_path, 'r', encoding='utf-8') as f:
                lead_data = json.load(f)
        
        # Extract timing information from transcript
        start_time = None
        end_time = None
        
        if "start_time" in transcript_data:
            start_time_str = transcript_data["start_time"]
            if isinstance(start_time_str, str):
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                except:
                    start_time = datetime.utcnow()
        
        if "end_time" in transcript_data:
            end_time_str = transcript_data["end_time"]
            if isinstance(end_time_str, str):
                try:
                    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                except:
                    end_time = datetime.utcnow()
        
        # Generate call ID if not provided
        if not call_id:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            call_id = f"CALL-{timestamp}-{transcript_data.get('session_id', 'unknown')[-8:]}"
        
        return upload_call_data_from_session(
            campaign_id=campaign_id,
            voice_agent_id=voice_agent_id,
            client_id=client_id,
            call_id=call_id,
            caller_phone=caller_phone,
            direction="inbound",
            start_time=start_time,
            end_time=end_time,
            status="completed",
            transcript_data=transcript_data,
            lead_data=lead_data
        )
        
    except Exception as e:
        logging.error(f"Failed to upload from transcript file {transcript_file_path}: {e}")
        return False

def bulk_upload_from_directory(
    conversations_dir: str,
    leads_dir: str,
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    default_caller_phone: str = "+919876543210"
) -> Dict[str, int]:
    """
    Upload all transcript and lead files from directories.
    
    Args:
        conversations_dir: Path to conversations directory
        leads_dir: Path to leads directory
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID
        client_id: Client ID
        default_caller_phone: Default phone number if not found in data
        
    Returns:
        Dict with success/failure counts
    """
    results = {"success": 0, "failed": 0, "total": 0}
    
    try:
        conversations_path = Path(conversations_dir)
        leads_path = Path(leads_dir)
        
        # Get all transcript session files
        transcript_files = list(conversations_path.glob("transcript_session_*.json"))
        
        for transcript_file in transcript_files:
            results["total"] += 1
            
            try:
                # Try to find matching lead file by timestamp
                # Extract timestamp from transcript filename
                filename = transcript_file.stem
                if "transcript_session_" in filename:
                    timestamp_part = filename.replace("transcript_session_", "")
                    
                    # Look for lead files with similar timestamp
                    lead_file = None
                    for lead_candidate in leads_path.glob("lead_*.json"):
                        # Simple matching - could be improved
                        lead_file = lead_candidate
                        break  # Take first available lead for now
                
                success = upload_from_transcript_file(
                    transcript_file_path=str(transcript_file),
                    campaign_id=campaign_id,
                    voice_agent_id=voice_agent_id,
                    client_id=client_id,
                    caller_phone=default_caller_phone,
                    lead_file_path=str(lead_file) if lead_file else None
                )
                
                if success:
                    results["success"] += 1
                    logging.info(f"Successfully uploaded {transcript_file.name}")
                else:
                    results["failed"] += 1
                    logging.error(f"Failed to upload {transcript_file.name}")
                    
            except Exception as e:
                results["failed"] += 1
                logging.error(f"Error processing {transcript_file.name}: {e}")
        
        logging.info(f"Bulk upload completed: {results}")
        return results
        
    except Exception as e:
        logging.error(f"Failed bulk upload: {e}")
        return results

# Example usage and testing
if __name__ == "__main__":
    # Example of uploading from current workspace
    import os
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Example configuration - replace with actual values
    CAMPAIGN_ID = "68c91223fde0aa95caa3dbe4"
    VOICE_AGENT_ID = "68c9105cfde0aa95caa3db64"
    CLIENT_ID = "68c90d626052ee95ac77059d"
    
    # Get current workspace paths
    workspace_dir = os.path.dirname(__file__)
    conversations_dir = os.path.join(workspace_dir, "conversations")
    leads_dir = os.path.join(workspace_dir, "leads")
    
    print(f"Looking for files in:")
    print(f"  Conversations: {conversations_dir}")
    print(f"  Leads: {leads_dir}")
    
    # Test bulk upload
    if os.path.exists(conversations_dir) and os.path.exists(leads_dir):
        results = bulk_upload_from_directory(
            conversations_dir=conversations_dir,
            leads_dir=leads_dir,
            campaign_id=CAMPAIGN_ID,
            voice_agent_id=VOICE_AGENT_ID,
            client_id=CLIENT_ID,
            default_caller_phone="+919876543210"
        )
        print(f"Upload results: {results}")
    else:
        print("Directories not found. Please check paths.")
        
    # Example of single file upload
    example_transcript = os.path.join(conversations_dir, "transcript_session_2025-10-23T07-56-34.661114.json")
    example_lead = os.path.join(leads_dir, "lead_20251013_135233.json")
    
    if os.path.exists(example_transcript):
        print(f"\nTesting single file upload: {example_transcript}")
        success = upload_from_transcript_file(
            transcript_file_path=example_transcript,
            campaign_id=CAMPAIGN_ID,
            voice_agent_id=VOICE_AGENT_ID,
            client_id=CLIENT_ID,
            caller_phone="+919876543210",
            call_id="TEST-CALL-001",
            lead_file_path=example_lead if os.path.exists(example_lead) else None
        )
        print(f"Single upload result: {'Success' if success else 'Failed'}")
    else:
        print(f"Example transcript file not found: {example_transcript}")