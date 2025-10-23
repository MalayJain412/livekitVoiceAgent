#!/usr/bin/env python3
"""
Example script showing how to use the CRM upload functionality
"""

import json
from datetime import datetime
from crm_upload import (
    upload_call_data_from_session,
    convert_transcript_to_api_format,
    convert_lead_to_api_format,
    create_call_details
)

def example_usage():
    """Demonstrate the CRM upload functionality"""
    
    print("CRM Upload Example")
    print("=" * 50)
    
    # Example configuration (replace with your actual values)
    CAMPAIGN_ID = "68c91223fde0aa95caa3dbe4"
    VOICE_AGENT_ID = "68c9105cfde0aa95caa3db64" 
    CLIENT_ID = "68c90d626052ee95ac77059d"
    CALLER_PHONE = "+919876543210"
    
    # Example transcript data (like what comes from transcript_logger.py)
    sample_transcript = {
        "session_id": "session_20251023_075614_example",
        "start_time": "2025-10-23T10:15:00Z",
        "end_time": "2025-10-23T10:18:30Z", 
        "duration_seconds": 210,
        "lead_generated": True,
        "items": [
            {
                "role": "assistant",
                "content": "Namaste! Main Urban Piper se piperbot bol rahi hoon. main aapki kaise madad kar sakti hoon?",
                "timestamp": "2025-10-23T10:15:00Z",
                "source": "agent"
            },
            {
                "role": "user",
                "content": "Hello, I'm interested in your AI voice solutions for my restaurant business",
                "timestamp": "2025-10-23T10:15:15Z",
                "source": "transcription_node",
                "transcript_confidence": 0.95
            },
            {
                "role": "assistant", 
                "content": "Great! I can help you with that. Can you tell me your name and company details?",
                "timestamp": "2025-10-23T10:15:20Z",
                "source": "agent"
            },
            {
                "role": "user",
                "content": "My name is Rajesh Kumar and I own Kumar Restaurants. I need help with order management.",
                "timestamp": "2025-10-23T10:15:35Z",
                "source": "transcription_node", 
                "transcript_confidence": 0.92
            }
        ],
        "metadata": {
            "persona": "piperbot",
            "caller_number": "+919876543210"
        }
    }
    
    # Example lead data (like what comes from tools.py create_lead)
    sample_lead = {
        "name": "Rajesh Kumar",
        "email": "rajesh@kumarrestaurants.com",
        "company": "Kumar Restaurants",
        "interest": "AI Voice Solutions for Order Management",
        "phone": "9876543210",
        "job_title": "Owner",
        "budget": "2-5 Lakhs",
        "timeline": "Next month",
        "timestamp": "2025-10-23T10:16:45Z",
        "source": "Friday AI Assistant",
        "status": "new"
    }
    
    print("\n1. Converting transcript data to API format:")
    converted_transcript = convert_transcript_to_api_format(sample_transcript)
    print(json.dumps(converted_transcript, indent=2))
    
    print("\n2. Converting lead data to API format:")
    converted_lead = convert_lead_to_api_format(sample_lead)
    print(json.dumps(converted_lead, indent=2))
    
    print("\n3. Creating call details:")
    call_details = create_call_details(
        call_id="CALL-EXAMPLE-001",
        direction="inbound",
        start_time=datetime(2025, 10, 23, 10, 15, 0),
        end_time=datetime(2025, 10, 23, 10, 18, 30),
        status="completed",
        caller_number="+919876543210"
    )
    print(json.dumps(call_details, indent=2, default=str))
    
    print("\n4. Complete API payload structure:")
    complete_payload = {
        "campaignId": CAMPAIGN_ID,
        "voiceAgentId": VOICE_AGENT_ID,
        "client": CLIENT_ID,
        "callDetails": call_details,
        "caller": {
            "phoneNumber": CALLER_PHONE
        },
        "transcription": converted_transcript,
        "lead": converted_lead
    }
    print(json.dumps(complete_payload, indent=2, default=str))
    
    print("\n5. To actually upload this data, you would call:")
    print(f"""
success = upload_call_data_from_session(
    campaign_id="{CAMPAIGN_ID}",
    voice_agent_id="{VOICE_AGENT_ID}", 
    client_id="{CLIENT_ID}",
    call_id="CALL-EXAMPLE-001",
    caller_phone="{CALLER_PHONE}",
    transcript_data=sample_transcript,
    lead_data=sample_lead
)
""")
    
    print("\n" + "=" * 50)
    print("Example completed!")
    print("\nTo enable automatic uploads:")
    print("Set environment variables:")
    print("  CRM_AUTO_UPLOAD=true")
    print(f"  CRM_CAMPAIGN_ID={CAMPAIGN_ID}")
    print(f"  CRM_VOICE_AGENT_ID={VOICE_AGENT_ID}")
    print(f"  CRM_CLIENT_ID={CLIENT_ID}")
    print(f"  CRM_DEFAULT_CALLER_PHONE={CALLER_PHONE}")

if __name__ == "__main__":
    example_usage()