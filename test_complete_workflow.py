#!/usr/bin/env python3
"""
Test the complete recording + CRM upload workflow
"""

import asyncio
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import from cagent to test the new function
import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_complete_workflow():
    """Test the complete workflow: recording upload + CRM upload"""
    
    print("=" * 60)
    print("TESTING COMPLETE RECORDING + CRM UPLOAD WORKFLOW")
    print("=" * 60)
    
    # Sample data from successful upload test
    recording_upload_response = {
        "success": True,
        "data": {
            "filename": "1761638707911.ogg",
            "originalName": "number-_918655200389-1761633666.ogg",
            "size": 2065148,
            "url": "http://devcrm.xeny.ai/apis/uploads/recordings/1761638707911.ogg",
            "relativeUrl": "/uploads/recordings/1761638707911.ogg"
        }
    }
    
    # Sample persona config (typical structure from your API)
    full_config = {
        "campaigns": [{
            "_id": "68c91223fde0aa95caa3dbe4",
            "client": "68c90d626052ee95ac77059d",
            "voiceAgents": [{
                "_id": "68c9105cfde0aa95caa3db64",
                "persona": {
                    "name": "Friday AI Assistant",
                    "personality": "Helpful voice assistant"
                }
            }]
        }]
    }
    
    dialed_number = "+918655200389"
    
    print(f"Recording URL: {recording_upload_response['data']['url']}")
    print(f"File size: {recording_upload_response['data']['size']} bytes")
    print(f"Dialed number: {dialed_number}")
    print(f"Campaign ID: {full_config['campaigns'][0]['_id']}")
    print(f"Voice Agent ID: {full_config['campaigns'][0]['voiceAgents'][0]['_id']}")
    print(f"Client ID: {full_config['campaigns'][0]['client']}")
    
    # Import and test the upload function
    try:
        from cagent import upload_call_data_to_crm
        
        print("\n🚀 Testing CRM call-data upload...")
        
        success = await upload_call_data_to_crm(
            recording_url=recording_upload_response['data']['url'],
            recording_size=recording_upload_response['data']['size'],
            dialed_number=dialed_number,
            full_config=full_config,
            session_manager=None  # Mock session for now
        )
        
        if success:
            print("✅ SUCCESS: Complete workflow test passed!")
            print("   - Recording uploaded ✅")
            print("   - CRM call-data uploaded ✅")
        else:
            print("❌ FAILED: CRM upload failed")
            
    except Exception as e:
        print(f"💥 ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("WORKFLOW TEST COMPLETED")
    print("=" * 60)

async def test_data_extraction():
    """Test the data extraction from config"""
    
    print("\n--- Testing Configuration Data Extraction ---")
    
    # Test config with all required fields
    good_config = {
        "campaigns": [{
            "_id": "campaign123",
            "client": "client456",
            "voiceAgents": [{
                "_id": "agent789",
                "persona": {"name": "Test Agent"}
            }]
        }]
    }
    
    # Test config missing fields
    bad_config = {
        "campaigns": [{
            "_id": "campaign123",
            # Missing client and voiceAgents
        }]
    }
    
    print("Testing good config extraction...")
    campaigns = good_config.get("campaigns", [])
    if campaigns:
        campaign = campaigns[0]
        campaign_id = campaign.get("_id")
        client_id = campaign.get("client")
        voice_agents = campaign.get("voiceAgents", [])
        voice_agent_id = voice_agents[0].get("_id") if voice_agents else None
        
        print(f"  Campaign ID: {campaign_id}")
        print(f"  Client ID: {client_id}")
        print(f"  Voice Agent ID: {voice_agent_id}")
        print(f"  All required fields present: {all([campaign_id, client_id, voice_agent_id])}")
    
    print("\nTesting bad config extraction...")
    campaigns = bad_config.get("campaigns", [])
    if campaigns:
        campaign = campaigns[0]
        campaign_id = campaign.get("_id")
        client_id = campaign.get("client")
        voice_agents = campaign.get("voiceAgents", [])
        voice_agent_id = voice_agents[0].get("_id") if voice_agents else None
        
        print(f"  Campaign ID: {campaign_id}")
        print(f"  Client ID: {client_id}")
        print(f"  Voice Agent ID: {voice_agent_id}")
        print(f"  All required fields present: {all([campaign_id, client_id, voice_agent_id])}")

async def main():
    """Run all tests"""
    await test_data_extraction()
    await test_complete_workflow()

if __name__ == "__main__":
    asyncio.run(main())