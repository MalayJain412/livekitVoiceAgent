#!/usr/bin/env python3
"""
Test CRM connectivity and upload functionality
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_crm_endpoints():
    """Test connectivity to CRM endpoints"""
    
    upload_url = "https://devcrm.xeny.ai/apis/api/public/upload"
    call_data_url = "https://devcrm.xeny.ai/apis/api/public/call-data"
    
    print("🧪 Testing CRM Connectivity...")
    print(f"Upload URL: {upload_url}")
    print(f"Call Data URL: {call_data_url}")
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        
        # Test upload endpoint
        print("\n📤 Testing upload endpoint...")
        try:
            async with session.options(upload_url) as resp:
                print(f"Upload endpoint status: {resp.status}")
                headers = dict(resp.headers)
                print(f"Headers: {json.dumps(headers, indent=2)}")
        except Exception as e:
            print(f"❌ Upload endpoint failed: {e}")
        
        # Test call-data endpoint  
        print("\n📊 Testing call-data endpoint...")
        try:
            async with session.options(call_data_url) as resp:
                print(f"Call-data endpoint status: {resp.status}")
                headers = dict(resp.headers)
                print(f"Headers: {json.dumps(headers, indent=2)}")
        except Exception as e:
            print(f"❌ Call-data endpoint failed: {e}")

        # Test with a minimal payload to call-data
        print("\n🔬 Testing call-data POST with minimal payload...")
        test_payload = {
            "campaignId": "test123",
            "voiceAgentId": "agent123", 
            "client": "client123",
            "callDetails": {
                "callId": f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "direction": "outbound",
                "startTime": datetime.now().isoformat(),
                "endTime": datetime.now().isoformat(),
                "duration": 30
            },
            "caller": {
                "phoneNumber": "+1234567890"
            },
            "transcription": {
                "text": "Test transcription",
                "events": []
            },
            "lead": {}
        }
        
        try:
            async with session.post(call_data_url, json=test_payload, timeout=15) as resp:
                print(f"POST status: {resp.status}")
                if resp.status < 400:
                    response_text = await resp.text()
                    print(f"✅ Success response: {response_text}")
                else:
                    error_text = await resp.text()
                    print(f"❌ Error response: {error_text}")
        except asyncio.TimeoutError:
            print("❌ Timeout: CRM endpoint took too long to respond")
        except Exception as e:
            print(f"❌ POST failed: {e}")

async def test_recording_detection():
    """Check if any recordings exist locally"""
    
    print("\n🎵 Checking for local recordings...")
    
    recording_dirs = [
        "recordings",
        "livekit-records", 
        "open-sip-records",
        "custom-recording"
    ]
    
    found_any = False
    
    for dir_name in recording_dirs:
        if os.path.exists(dir_name):
            files = os.listdir(dir_name)
            if files:
                print(f"📁 {dir_name}: {len(files)} files")
                for f in files[:5]:  # Show first 5 files
                    full_path = os.path.join(dir_name, f)
                    size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                    print(f"  - {f} ({size} bytes)")
                if len(files) > 5:
                    print(f"  ... and {len(files) - 5} more files")
                found_any = True
            else:
                print(f"📁 {dir_name}: empty")
        else:
            print(f"📁 {dir_name}: not found")
    
    if not found_any:
        print("❌ No recordings found in any directory")
    
    return found_any

async def test_livekit_api_install():
    """Check LiveKit API availability"""
    
    print("\n🔧 Checking LiveKit API availability...")
    
    try:
        import livekit
        from livekit.api import LiveKitAPI
        print("✅ LiveKit API imported successfully")
        
        # Try to create an instance
        try:
            api = LiveKitAPI("ws://localhost:7880", "test", "test")
            print("✅ LiveKit API instance created")
        except Exception as e:
            print(f"⚠️ LiveKit API instance creation failed: {e}")
            
    except ImportError as e:
        print(f"❌ LiveKit API import failed: {e}")
        print("💡 Try: pip install livekit-api")
        
        # Check if livekit-agents is installed
        try:
            import livekit.agents
            print("✅ livekit-agents is available")
        except ImportError:
            print("❌ livekit-agents also not available")

async def main():
    print("=" * 60)
    print("CRM CONNECTIVITY & RECORDING TEST")
    print("=" * 60)
    
    await test_crm_endpoints()
    await test_recording_detection() 
    await test_livekit_api_install()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())