"""
Mobile API Integration
Retrieves campaign and voice agent configuration from mobile number API
"""

import logging
import requests
from typing import Optional, Dict, Any
import os

# Mobile API endpoint
MOBILE_API_URL = "https://devcrm.xeny.ai/apis/api/public/mobile"

def get_campaign_config_from_mobile(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Get campaign and voice agent configuration from mobile number API.
    
    Args:
        phone_number: Phone number (e.g., "+918655066243")
        
    Returns:
        Dict containing campaignId, voiceAgentId, client, etc.
        None if API call fails
        
    Example response:
    {
        "campaignId": "68c91223fde0aa95caa3dbe4",
        "voiceAgentId": "68c9105cfde0aa95caa3db64", 
        "client": "68c90d626052ee95ac77059d",
        "personaName": "Friday AI Assistant",
        "businessInfo": {...}
    }
    """
    try:
        # Clean phone number (remove + if present for URL)
        clean_number = phone_number.lstrip('+')
        url = f"{MOBILE_API_URL}/{clean_number}"
        
        logging.info(f"Fetching campaign config from mobile API: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse the actual API response structure
            if isinstance(data, dict) and 'campaigns' in data:
                campaigns = data.get('campaigns', [])
                
                if campaigns and len(campaigns) > 0:
                    # Get first active campaign
                    campaign = campaigns[0]
                    campaign_id = campaign.get('campaignId')
                    client_info = campaign.get('client', {})
                    client_id = client_info.get('id')
                    
                    # Get first voice agent
                    voice_agents = campaign.get('voiceAgents', [])
                    if voice_agents and len(voice_agents) > 0:
                        voice_agent = voice_agents[0]
                        voice_agent_id = voice_agent.get('id')
                        
                        if campaign_id and voice_agent_id and client_id:
                            result = {
                                'campaignId': campaign_id,
                                'voiceAgentId': voice_agent_id,
                                'client': client_id,
                                'personaName': voice_agent.get('name', 'AI Assistant'),
                                'campaignName': campaign.get('campaignName', ''),
                                'clientName': client_info.get('name', ''),
                                'voiceDetails': voice_agent.get('voiceDetails', {})
                            }
                            logging.info(f"Mobile API success: campaign={campaign_id}, voice={voice_agent_id}, client={client_id}")
                            return result
                
                logging.warning(f"Mobile API response missing required campaign/voice data: {data}")
            else:
                logging.warning(f"Mobile API response format unexpected: {data}")
                
        else:
            logging.error(f"Mobile API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        logging.error(f"Mobile API timeout for number: {phone_number}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Mobile API request failed for {phone_number}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error calling mobile API for {phone_number}: {e}")
    
    return None

def get_campaign_metadata_for_call(phone_number: str, session_id: str) -> Dict[str, str]:
    """
    Get complete metadata for file naming and matching.
    
    Args:
        phone_number: Dialed phone number
        session_id: Current session ID
        
    Returns:
        Dict with campaignId, voiceAgentId, sessionId for file naming
    """
    # Get config from mobile API
    mobile_config = get_campaign_config_from_mobile(phone_number)
    
    if mobile_config:
        campaign_id = mobile_config.get('campaignId', 'unknown')
        voice_agent_id = mobile_config.get('voiceAgentId', 'unknown')
        client_id = mobile_config.get('client', 'unknown')
    else:
        # Fallback to environment defaults
        campaign_id = os.getenv("DEFAULT_CAMPAIGN_ID", "68c91223fde0aa95caa3dbe4")
        voice_agent_id = os.getenv("DEFAULT_VOICE_AGENT_ID", "68c9105cfde0aa95caa3db64")
        client_id = os.getenv("DEFAULT_CLIENT_ID", "68c90d626052ee95ac77059d")
        
        logging.warning(f"Using fallback campaign config for {phone_number}")
    
    metadata = {
        "campaignId": campaign_id,
        "voiceAgentId": voice_agent_id,
        "clientId": client_id,
        "sessionId": session_id,
        "dialedNumber": phone_number
    }
    
    logging.info(f"Campaign metadata: {metadata}")
    return metadata

def generate_metadata_filename(base_name: str, metadata: Dict[str, str], extension: str = ".json") -> str:
    """
    Generate filename with embedded metadata for reliable matching.
    
    Args:
        base_name: Base filename (e.g., "transcript_session", "lead", "recording")
        metadata: Metadata dict with campaignId, voiceAgentId, sessionId
        extension: File extension
        
    Returns:
        Filename like: transcript_session_CAMP123_VA456_SESSION789.json
    """
    campaign_id = metadata.get('campaignId', 'unknown')[:12]  # Truncate for filename
    voice_agent_id = metadata.get('voiceAgentId', 'unknown')[:12]
    session_id = metadata.get('sessionId', 'unknown')[:16]
    
    # Clean IDs for filename (remove special chars)
    campaign_clean = ''.join(c for c in campaign_id if c.isalnum())
    voice_clean = ''.join(c for c in voice_agent_id if c.isalnum()) 
    session_clean = ''.join(c for c in session_id if c.isalnum())
    
    filename = f"{base_name}_{campaign_clean}_{voice_clean}_{session_clean}{extension}"
    return filename

def extract_metadata_from_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Extract metadata from filename with embedded IDs.
    
    Args:
        filename: Filename like transcript_session_CAMP123_VA456_SESSION789.json
        
    Returns:
        Dict with campaignId, voiceAgentId, sessionId or None if can't parse
    """
    try:
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Split by underscore and look for the last 3 parts
        parts = name_without_ext.split('_')
        
        if len(parts) >= 4:  # base_name + 3 ID parts
            campaign_part = parts[-3]
            voice_part = parts[-2]
            session_part = parts[-1]
            
            # Return the extracted parts (they're cleaned IDs)
            return {
                "campaignId": campaign_part,
                "voiceAgentId": voice_part, 
                "sessionId": session_part
            }
    except Exception as e:
        logging.error(f"Error extracting metadata from filename {filename}: {e}")
    
    return None

def match_files_by_metadata(conversation_files: list, recording_files: list, lead_files: list) -> list:
    """
    Match conversation, recording, and lead files by embedded metadata.
    
    Args:
        conversation_files: List of conversation file paths
        recording_files: List of recording file paths  
        lead_files: List of lead file paths
        
    Returns:
        List of matched file sets: [(conv_file, rec_file, lead_file), ...]
    """
    matched_sets = []
    
    for conv_file in conversation_files:
        conv_metadata = extract_metadata_from_filename(conv_file)
        if not conv_metadata:
            continue
            
        # Find matching recording
        matching_recording = None
        for rec_file in recording_files:
            rec_metadata = extract_metadata_from_filename(rec_file)
            if rec_metadata and rec_metadata == conv_metadata:
                matching_recording = rec_file
                break
        
        # Find matching lead  
        matching_lead = None
        for lead_file in lead_files:
            lead_metadata = extract_metadata_from_filename(lead_file)
            if lead_metadata and lead_metadata == conv_metadata:
                matching_lead = lead_file
                break
        
        # Add to matched sets (recording and lead are optional)
        matched_sets.append((conv_file, matching_recording, matching_lead))
        
        logging.info(f"Matched set: conv={conv_file}, rec={matching_recording}, lead={matching_lead}")
    
    return matched_sets

# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test mobile API
    test_number = "+918655066243"
    config = get_campaign_config_from_mobile(test_number)
    print(f"Mobile API result: {config}")
    
    # Test metadata generation
    if config:
        metadata = get_campaign_metadata_for_call(test_number, "session_123456")
        print(f"Metadata: {metadata}")
        
        # Test filename generation
        filename = generate_metadata_filename("transcript_session", metadata)
        print(f"Generated filename: {filename}")
        
        # Test extraction
        extracted = extract_metadata_from_filename(filename)
        print(f"Extracted metadata: {extracted}")