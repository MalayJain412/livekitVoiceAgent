#!/usr/bin/env python3
"""
Test script for CRM upload functionality
"""

import os
import json
import logging
from datetime import datetime
from crm_upload import (
    upload_call_data_from_session,
    upload_from_transcript_file,
    bulk_upload_from_directory,
    convert_transcript_to_api_format,
    convert_lead_to_api_format
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_data_conversion():
    """Test data conversion functions"""
    print("=== Testing Data Conversion ===")
    
    # Test transcript conversion
    sample_transcript = {
        "session_id": "session_20251023_075614_7e155942",
        "start_time": "2025-10-23 07:56:34.608343",
        "end_time": "2025-10-23 07:56:34.608343",
        "duration_seconds": 30,
        "lead_generated": False,
        "items": [
            {
                "role": "assistant",
                "content": "Namaste! Main Urban Piper se piperbot bol rahi hoon.",
                "timestamp": "2025-10-23T07:56:34.608343Z"
            },
            {
                "role": "user",
                "content": "Hello, I need help",
                "timestamp": "2025-10-23T07:56:44.608343Z",
                "transcript_confidence": 0.95
            }
        ]
    }
    
    converted_transcript = convert_transcript_to_api_format(sample_transcript)
    print(f"Converted transcript: {json.dumps(converted_transcript, indent=2)}")
    
    # Test lead conversion
    sample_lead = {
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Tech Corp",
        "interest": "AI Solutions",
        "phone": "9876543210",
        "budget": "50k-100k",
        "timestamp": "2025-10-23T07:56:34.608343Z"
    }
    
    converted_lead = convert_lead_to_api_format(sample_lead)
    print(f"Converted lead: {json.dumps(converted_lead, indent=2)}")

def test_single_upload():
    """Test single file upload"""
    print("\n=== Testing Single File Upload ===")
    
    # Configuration - replace with actual values
    CAMPAIGN_ID = "68c91223fde0aa95caa3dbe4"
    VOICE_AGENT_ID = "68c9105cfde0aa95caa3db64"
    CLIENT_ID = "68c90d626052ee95ac77059d"
    
    # Test with actual files from workspace
    workspace_dir = os.path.dirname(__file__)
    conversations_dir = os.path.join(workspace_dir, "conversations")
    leads_dir = os.path.join(workspace_dir, "leads")
    
    # Find a transcript file to test with
    transcript_file = os.path.join(conversations_dir, "transcript_session_2025-10-23T07-56-34.661114.json")
    lead_file = os.path.join(leads_dir, "lead_20251013_135233.json")
    
    if os.path.exists(transcript_file):
        print(f"Testing upload with: {transcript_file}")
        
        # Note: This will make an actual API call - uncomment to test
        # success = upload_from_transcript_file(
        #     transcript_file_path=transcript_file,
        #     campaign_id=CAMPAIGN_ID,
        #     voice_agent_id=VOICE_AGENT_ID,
        #     client_id=CLIENT_ID,
        #     caller_phone="+919876543210",
        #     call_id="TEST-CALL-DEMO",
        #     lead_file_path=lead_file if os.path.exists(lead_file) else None
        # )
        # print(f"Upload result: {'Success' if success else 'Failed'}")
        
        print("Upload test commented out to avoid actual API calls. Uncomment to test.")
    else:
        print(f"Transcript file not found: {transcript_file}")

def test_bulk_upload():
    """Test bulk upload functionality"""
    print("\n=== Testing Bulk Upload ===")
    
    # Configuration
    CAMPAIGN_ID = "68c91223fde0aa95caa3dbe4"
    VOICE_AGENT_ID = "68c9105cfde0aa95caa3db64"
    CLIENT_ID = "68c90d626052ee95ac77059d"
    
    workspace_dir = os.path.dirname(__file__)
    conversations_dir = os.path.join(workspace_dir, "conversations")
    leads_dir = os.path.join(workspace_dir, "leads")
    
    print(f"Conversations directory: {conversations_dir}")
    print(f"Leads directory: {leads_dir}")
    
    if os.path.exists(conversations_dir) and os.path.exists(leads_dir):
        # List available files
        transcript_files = [f for f in os.listdir(conversations_dir) if f.startswith("transcript_session_") and f.endswith(".json")]
        lead_files = [f for f in os.listdir(leads_dir) if f.startswith("lead_") and f.endswith(".json")]
        
        print(f"Found {len(transcript_files)} transcript files")
        print(f"Found {len(lead_files)} lead files")
        
        # Note: This will make actual API calls - uncomment to test
        # results = bulk_upload_from_directory(
        #     conversations_dir=conversations_dir,
        #     leads_dir=leads_dir,
        #     campaign_id=CAMPAIGN_ID,
        #     voice_agent_id=VOICE_AGENT_ID,
        #     client_id=CLIENT_ID,
        #     default_caller_phone="+919876543210"
        # )
        # print(f"Bulk upload results: {results}")
        
        print("Bulk upload test commented out to avoid actual API calls. Uncomment to test.")
    else:
        print("Required directories not found")

def test_payload_structure():
    """Test the payload structure matches the API requirements"""
    print("\n=== Testing Payload Structure ===")
    
    # Create a sample payload
    from crm_upload import create_call_details
    
    call_details = create_call_details(
        call_id="CALL-20250929-001",
        direction="inbound",
        start_time=datetime(2025, 9, 29, 10, 15, 0),
        end_time=datetime(2025, 9, 29, 10, 20, 30),
        status="completed",
        recording_url="http://devcrm.xeny.ai/apis/uploads/recordings/1759173049893.wav",
        recording_duration=330,
        recording_size=2456789,
        caller_number="+919876543210"
    )
    
    caller = {
        "phoneNumber": "+919876543210"
    }
    
    sample_transcript = {
        "session_id": "test_session",
        "conversation_items": [
            {"role": "assistant", "content": "Hello", "timestamp": "2025-09-29T10:15:00Z"},
            {"role": "user", "content": "Hi there", "timestamp": "2025-09-29T10:15:05Z"}
        ]
    }
    
    sample_lead = {
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Tech Corp",
        "interest": "AI Solutions"
    }
    
    payload = {
        "campaignId": "68c91223fde0aa95caa3dbe4",
        "voiceAgentId": "68c9105cfde0aa95caa3db64",
        "client": "68c90d626052ee95ac77059d",
        "callDetails": call_details,
        "caller": caller,
        "transcription": sample_transcript,
        "lead": sample_lead
    }
    
    print("Sample payload structure:")
    print(json.dumps(payload, indent=2, default=str))

if __name__ == "__main__":
    print("CRM Upload Test Suite")
    print("=" * 50)
    
    test_data_conversion()
    test_payload_structure()
    test_single_upload()
    test_bulk_upload()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("\nTo run actual API tests:")
    print("1. Uncomment the API call lines in test functions")
    print("2. Ensure you have valid campaign_id, voice_agent_id, and client_id")
    print("3. Check your network connection")