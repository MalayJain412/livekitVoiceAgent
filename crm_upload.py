"""
CRM Upload Module
Handles uploading call data (transcription and lead) to CRM API
"""

import logging
import requests
import json
import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# API endpoints
CRM_UPLOAD_URL = "https://devcrm.xeny.ai/apis/api/public/call-data"
CRM_FILE_UPLOAD_URL = "https://devcrm.xeny.ai/apis/api/public/upload"

async def upload_recording_file(file_path: str) -> Optional[str]:
    """
    Upload recording file to CRM storage API.
    
    Args:
        file_path: Path to the recording file (.ogg)
        
    Returns:
        str: Recording URL if upload successful, None otherwise
    """
    try:
        if not os.path.exists(file_path):
            logging.error(f"Recording file not found: {file_path}")
            return None
            
        file_size = os.path.getsize(file_path)
        logging.info(f"Uploading recording file: {file_path} ({file_size} bytes)")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            # Prepare multipart form data
            with open(file_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, 
                                  filename=os.path.basename(file_path),
                                  content_type='audio/ogg')
                
                async with session.post(CRM_FILE_UPLOAD_URL, data=form_data) as response:
                    if response.status >= 200 and response.status < 300:
                        response_data = await response.json()
                        
                        if response_data.get('success'):
                            recording_url = response_data['data']['url']
                            original_name = response_data['data']['originalName']
                            uploaded_size = response_data['data']['size']
                            
                            logging.info(f"Recording uploaded successfully:")
                            logging.info(f"  Original: {original_name}")
                            logging.info(f"  URL: {recording_url}")
                            logging.info(f"  Size: {uploaded_size} bytes")
                            
                            return recording_url
                        else:
                            logging.error(f"Upload failed: {response_data}")
                            return None
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to upload recording. Status: {response.status}, Error: {error_text}")
                        return None
                        
    except Exception as e:
        logging.error(f"Error uploading recording file {file_path}: {e}", exc_info=True)
        return None

def upload_recording_file_sync(file_path: str) -> Optional[str]:
    """
    Synchronous wrapper for upload_recording_file.
    
    Args:
        file_path: Path to the recording file (.ogg)
        
    Returns:
        str: Recording URL if upload successful, None otherwise
    """
    try:
        if not os.path.exists(file_path):
            logging.error(f"Recording file not found: {file_path}")
            return None
            
        file_size = os.path.getsize(file_path)
        logging.info(f"Uploading recording file: {file_path} ({file_size} bytes)")
        
        # Prepare multipart form data
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'audio/ogg')}
            
            response = requests.post(
                CRM_FILE_UPLOAD_URL,
                files=files,
                timeout=60
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                response_data = response.json()
                
                if response_data.get('success'):
                    recording_url = response_data['data']['url']
                    original_name = response_data['data']['originalName']
                    uploaded_size = response_data['data']['size']
                    
                    logging.info(f"Recording uploaded successfully:")
                    logging.info(f"  Original: {original_name}")
                    logging.info(f"  URL: {recording_url}")
                    logging.info(f"  Size: {uploaded_size} bytes")
                    
                    return recording_url
                else:
                    logging.error(f"Upload failed: {response_data}")
                    return None
            else:
                logging.error(f"Failed to upload recording. Status: {response.status_code}, Error: {response.text}")
                return None
                
    except Exception as e:
        logging.error(f"Error uploading recording file {file_path}: {e}", exc_info=True)
        return None

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

async def upload_complete_call_data(
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    call_id: str,
    caller_phone: str,
    conversation_data: Dict[str, Any],
    recording_file_path: Optional[str] = None,
    direction: str = "inbound",
    status: str = "completed"
) -> bool:
    """
    Complete upload workflow: Upload recording file first, then upload call data with recording URL.
    This is the recommended function for the directory-based cron approach.
    
    Args:
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID  
        client_id: Client ID
        call_id: Unique call identifier
        caller_phone: Caller's phone number
        conversation_data: MongoDB conversation data (conversation file format)
        recording_file_path: Path to recording file (.ogg) - will upload first to get URL
        direction: Call direction (inbound/outbound)
        status: Call status
        
    Returns:
        bool: True if complete upload successful, False otherwise
    """
    recording_url = None
    recording_size = None
    
    # Step 1: Upload recording file if provided
    if recording_file_path and os.path.exists(recording_file_path):
        logging.info(f"Step 1: Uploading recording file: {recording_file_path}")
        recording_url = await upload_recording_file(recording_file_path)
        
        if recording_url:
            recording_size = os.path.getsize(recording_file_path)
            logging.info(f"Recording upload successful, URL: {recording_url}")
        else:
            logging.error(f"Recording upload failed for: {recording_file_path}")
            # Continue without recording URL - call data can still be uploaded
    else:
        logging.warning(f"No recording file provided or file not found: {recording_file_path}")
    
    # Step 2: Upload call data with recording URL
    logging.info(f"Step 2: Uploading call data with recording URL")
    success = await upload_call_data_from_conversation(
        campaign_id=campaign_id,
        voice_agent_id=voice_agent_id,
        client_id=client_id,
        call_id=call_id,
        caller_phone=caller_phone,
        conversation_data=conversation_data,
        recording_url=recording_url,
        recording_size=recording_size,
        direction=direction,
        status=status
    )
    
    if success:
        logging.info(f"Complete upload successful for call ID: {call_id}")
    else:
        logging.error(f"Call data upload failed for call ID: {call_id}")
    
    return success

def upload_complete_call_data_sync(
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    call_id: str,
    caller_phone: str,
    conversation_data: Dict[str, Any],
    recording_file_path: Optional[str] = None,
    direction: str = "inbound",
    status: str = "completed"
) -> bool:
    """
    Synchronous wrapper for upload_complete_call_data.
    Perfect for cron jobs that need simple sync operation.
    
    Args:
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID  
        client_id: Client ID
        call_id: Unique call identifier
        caller_phone: Caller's phone number
        conversation_data: MongoDB conversation data
        recording_file_path: Path to recording file (.ogg)
        direction: Call direction (inbound/outbound)
        status: Call status
        
    Returns:
        bool: True if complete upload successful, False otherwise
    """
    recording_url = None
    recording_size = None
    
    # Step 1: Upload recording file if provided
    if recording_file_path and os.path.exists(recording_file_path):
        logging.info(f"Step 1: Uploading recording file: {recording_file_path}")
        recording_url = upload_recording_file_sync(recording_file_path)
        
        if recording_url:
            recording_size = os.path.getsize(recording_file_path)
            logging.info(f"Recording upload successful, URL: {recording_url}")
        else:
            logging.error(f"Recording upload failed for: {recording_file_path}")
            # Continue without recording URL - call data can still be uploaded
    else:
        logging.warning(f"No recording file provided or file not found: {recording_file_path}")
    
    # Step 2: Upload call data with recording URL (using sync version)
    logging.info(f"Step 2: Uploading call data with recording URL")
    
    # Convert conversation data and upload
    try:
        # Use the existing sync upload_call_data_from_conversation logic but with recording URL
        # We'll reuse the format conversion from the async version
        
        # Extract conversation items in the proper format
        conversation_items = []
        for item in conversation_data.get('items', []):
            role = item.get('role', 'unknown')
            if role == 'unknown' and item.get('type'):
                role = item.get('type')
            
            content = item.get('content', '')
            if isinstance(content, list):
                content = ' '.join(str(c) for c in content)
            
            # Skip empty content items (like persona_applied)
            if not content and role in ['persona_applied', 'unknown']:
                continue
                
            conversation_items.append({
                "role": role,
                "content": str(content),
                "timestamp": item.get('timestamp', ''),
                "source": item.get('source', 'unknown'),
                "transcript_confidence": item.get('transcript_confidence')
            })
        
        # Extract timing information
        start_time = conversation_data.get('start_time', '')
        end_time = conversation_data.get('end_time', '')
        duration = int(conversation_data.get('duration_seconds', 0))
        
        # Ensure proper ISO format for CRM API
        def parse_timestamp_robust(timestamp):
            """Robust timestamp parsing for CRM API compatibility"""
            try:
                if not timestamp:
                    return datetime.utcnow().isoformat() + "Z"
                    
                if isinstance(timestamp, str):
                    # Handle format: "2025-10-28 06:27:29.508221+00:00"
                    if ' ' in timestamp and '+' in timestamp:
                        # Replace space with T and ensure Z ending
                        timestamp = timestamp.replace(' ', 'T').replace('+00:00', 'Z')
                    elif 'T' in timestamp and timestamp.endswith('+00:00'):
                        # Replace timezone with Z
                        timestamp = timestamp.replace('+00:00', 'Z')
                    elif 'T' in timestamp and not timestamp.endswith('Z'):
                        # Ensure Z ending for UTC
                        timestamp = timestamp.rstrip('Z') + 'Z'
                        
                return timestamp
            except Exception as e:
                logging.warning(f"Error parsing timestamp {timestamp}: {e}")
                return datetime.utcnow().isoformat() + "Z"
        
        start_time = parse_timestamp_robust(start_time)
        end_time = parse_timestamp_robust(end_time)
        
        # Build the exact payload structure that worked in tests
        payload = {
            "campaignId": campaign_id,
            "voiceAgentId": voice_agent_id,
            "client": client_id,
            "callDetails": {
                "callId": call_id,
                "direction": direction,
                "startTime": start_time,
                "endTime": end_time,
                "duration": duration,
                "status": status,
                "callerNumber": caller_phone,
                "recordingUrl": recording_url,
                "recordingDuration": duration,
                "recordingSize": recording_size
            },
            "caller": {
                "phoneNumber": caller_phone
            },
            "transcription": {
                "session_id": conversation_data.get('session_id'),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": conversation_data.get('duration_seconds'),
                "total_items": len(conversation_items),
                "conversation_items": conversation_items,
                "lead_generated": conversation_data.get('lead_generated', False),
                "metadata": conversation_data.get('metadata', {})
            },
            "lead": conversation_data.get('lead', {})
        }
        
        logging.info(f"Uploading call data for call ID: {call_id}")
        logging.info(f"Payload size: {len(json.dumps(payload))} characters")
        logging.info(f"Conversation items: {len(conversation_items)}")
        
        # Upload to CRM API using requests
        response = requests.post(
            CRM_UPLOAD_URL,
            json=payload,
            timeout=30
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            logging.info(f"Successfully uploaded call data to CRM. Response: {response.status_code}")
            logging.info(f"Complete upload successful for call ID: {call_id}")
            return True
        else:
            logging.error(f"Failed to upload call data to CRM. Status: {response.status_code}, Error: {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Error uploading call data to CRM: {e}", exc_info=True)
        return False

async def upload_call_data_from_conversation(
    campaign_id: str,
    voice_agent_id: str,
    client_id: str,
    call_id: str,
    caller_phone: str,
    conversation_data: Dict[str, Any],
    recording_url: Optional[str] = None,
    recording_size: Optional[int] = None,
    direction: str = "inbound",
    status: str = "completed"
) -> bool:
    """
    Upload call data using MongoDB conversation format (working format).
    This matches the successful test payload structure.
    
    Args:
        campaign_id: Campaign ID
        voice_agent_id: Voice Agent ID  
        client_id: Client ID
        call_id: Unique call identifier
        caller_phone: Caller's phone number
        conversation_data: MongoDB conversation data (conversation file format)
        recording_url: URL to call recording
        recording_size: Recording file size in bytes
        direction: Call direction (inbound/outbound)
        status: Call status
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    import aiohttp
    
    try:
        # Extract conversation items in the proper format
        conversation_items = []
        for item in conversation_data.get('items', []):
            role = item.get('role', 'unknown')
            if role == 'unknown' and item.get('type'):
                role = item.get('type')
            
            content = item.get('content', '')
            if isinstance(content, list):
                content = ' '.join(str(c) for c in content)
            
            # Skip empty content items (like persona_applied)
            if not content and role in ['persona_applied', 'unknown']:
                continue
                
            conversation_items.append({
                "role": role,
                "content": str(content),
                "timestamp": item.get('timestamp', ''),
                "source": item.get('source', 'unknown'),
                "transcript_confidence": item.get('transcript_confidence')
            })
        
        # Extract timing information
        start_time = conversation_data.get('start_time', '')
        end_time = conversation_data.get('end_time', '')
        duration = int(conversation_data.get('duration_seconds', 0))
        
        # Ensure proper ISO format for CRM API
        def parse_timestamp_robust(timestamp):
            """Robust timestamp parsing for CRM API compatibility"""
            try:
                if not timestamp:
                    return datetime.utcnow().isoformat() + "Z"
                    
                if isinstance(timestamp, str):
                    # Handle format: "2025-10-28 06:27:29.508221+00:00"
                    if ' ' in timestamp and '+' in timestamp:
                        # Replace space with T and ensure Z ending
                        timestamp = timestamp.replace(' ', 'T').replace('+00:00', 'Z')
                    elif 'T' in timestamp and timestamp.endswith('+00:00'):
                        # Replace timezone with Z
                        timestamp = timestamp.replace('+00:00', 'Z')
                    elif 'T' in timestamp and not timestamp.endswith('Z'):
                        # Ensure Z ending for UTC
                        timestamp = timestamp.rstrip('Z') + 'Z'
                        
                return timestamp
            except Exception as e:
                logging.warning(f"Error parsing timestamp {timestamp}: {e}")
                return datetime.utcnow().isoformat() + "Z"
        
        start_time = parse_timestamp_robust(start_time)
        end_time = parse_timestamp_robust(end_time)
        
        # Build the exact payload structure that worked in tests
        payload = {
            "campaignId": campaign_id,
            "voiceAgentId": voice_agent_id,
            "client": client_id,
            "callDetails": {
                "callId": call_id,
                "direction": direction,
                "startTime": start_time,
                "endTime": end_time,
                "duration": duration,
                "status": status,
                "callerNumber": caller_phone,
                "recordingUrl": recording_url,
                "recordingDuration": duration,
                "recordingSize": recording_size
            },
            "caller": {
                "phoneNumber": caller_phone
            },
            "transcription": {
                "session_id": conversation_data.get('session_id'),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": conversation_data.get('duration_seconds'),
                "total_items": len(conversation_items),
                "conversation_items": conversation_items,
                "lead_generated": conversation_data.get('lead_generated', False),
                "metadata": conversation_data.get('metadata', {})
            },
            "lead": conversation_data.get('lead', {})
        }
        
        logging.info(f"Uploading call data for call ID: {call_id}")
        logging.info(f"Payload size: {len(json.dumps(payload))} characters")
        logging.info(f"Conversation items: {len(conversation_items)}")
        
        # Upload to CRM API
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(CRM_UPLOAD_URL, json=payload) as response:
                if response.status >= 200 and response.status < 300:
                    response_data = await response.json()
                    logging.info(f"Successfully uploaded call data to CRM. Response: {response.status}")
                    logging.debug(f"CRM response: {response_data}")
                    return True
                else:
                    error_text = await response.text()
                    logging.error(f"Failed to upload call data to CRM. Status: {response.status}, Error: {error_text}")
                    return False
                    
    except Exception as e:
        logging.error(f"Error uploading call data to CRM: {e}", exc_info=True)
        return False

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
    DEPRECATED: Use upload_call_data_from_conversation instead.
    This is kept for backward compatibility.
    
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
        
        # Get all MongoDB-formatted transcript session files (ignore raw transcript dumps)
        transcript_files = list(conversations_path.glob("transcript_session_*.json"))
        
        # Filter out raw transcript files (they don't have proper session structure)
        mongodb_files = []
        for transcript_file in transcript_files:
            # Only include files that match the MongoDB session format
            if transcript_file.name.startswith("transcript_session_"):
                # Verify it's a MongoDB-formatted file by checking structure
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Check if it has MongoDB format fields
                    if isinstance(data, dict) and 'session_id' in data and 'items' in data:
                        mongodb_files.append(transcript_file)
                except:
                    # Skip files that can't be parsed or don't have the right structure
                    continue
        
        logging.info(f"Found {len(mongodb_files)} MongoDB-formatted transcript files to upload")
        
        for transcript_file in mongodb_files:
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