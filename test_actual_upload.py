#!/usr/bin/env python3
"""
Test actual recording upload and CRM data upload
"""

import asyncio
import aiohttp
import aiofiles
import json
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_recording_upload():
    """Test uploading an actual recording file"""
    
    recording_file = "recordings/number-_918655200389-1761633666.ogg"
    upload_url = "https://devcrm.xeny.ai/apis/api/public/upload"
    
    if not os.path.exists(recording_file):
        print(f"❌ Recording file not found: {recording_file}")
        return None
    
    file_size = os.path.getsize(recording_file)
    print(f"📁 Recording file: {recording_file}")
    print(f"📊 File size: {file_size:,} bytes")
    
    print(f"\n📤 Uploading to: {upload_url}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            
            async with aiofiles.open(recording_file, 'rb') as f:
                file_content = await f.read()
            
            data.add_field('file', 
                          file_content,
                          filename=os.path.basename(recording_file),
                          content_type='audio/ogg')
            
            print(f"🚀 Starting upload...")
            
            async with session.post(upload_url, data=data) as resp:
                print(f"📊 Response status: {resp.status}")
                
                if resp.status < 400:
                    response_data = await resp.json()
                    print(f"✅ Upload successful!")
                    print(f"📄 Response: {json.dumps(response_data, indent=2)}")
                    
                    # Extract file URL if available
                    if 'data' in response_data and 'url' in response_data['data']:
                        file_url = response_data['data']['url']
                        print(f"🔗 File URL: {file_url}")
                        return file_url
                    
                else:
                    error_text = await resp.text()
                    print(f"❌ Upload failed: {error_text}")
                    return None
                    
    except asyncio.TimeoutError:
        print("❌ Upload timeout")
        return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

async def test_call_data_upload(recording_url=None):
    """Test CRM call-data upload with actual data"""
    
    call_data_url = "https://devcrm.xeny.ai/apis/api/public/call-data"
    
    # Build realistic payload
    timestamp = datetime.now()
    payload = {
        "campaignId": "68c91223fde0aa95caa3dbe4",  # From persona handler
        "voiceAgentId": "68c9105cfde0aa95caa3db64",  # From persona handler
        "client": "68c90d626052ee95ac77059d",  # From persona handler
        "callDetails": {
            "callId": f"TEST-{timestamp.strftime('%Y%m%d-%H%M%S')}-55200389",
            "direction": "outbound",
            "startTime": timestamp.isoformat(),
            "endTime": (timestamp).isoformat(),  # 2 min call
            "duration": 120,
            "recordingUrl": recording_url
        },
        "caller": {
            "phoneNumber": "+918655200389"
        },
        "transcription": {
            "text": "Hello, how are you? I'm fine, thank you. Can you help me with something? Yes, I can help you.",
            "events": [
                {"timestamp": timestamp.isoformat(), "speaker": "user", "text": "Hello, how are you?"},
                {"timestamp": timestamp.isoformat(), "speaker": "assistant", "text": "I'm fine, thank you. Can you help me with something?"},
                {"timestamp": timestamp.isoformat(), "speaker": "user", "text": "Yes, I can help you."}
            ]
        },
        "lead": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+918655200389",
            "company": "Test Company",
            "interest": "product demo"
        }
    }
    
    print(f"\n📊 Testing call-data upload to: {call_data_url}")
    print(f"🎯 Payload preview:")
    print(f"  Campaign ID: {payload['campaignId']}")
    print(f"  Voice Agent ID: {payload['voiceAgentId']}")
    print(f"  Call ID: {payload['callDetails']['callId']}")
    print(f"  Recording URL: {payload['callDetails'].get('recordingUrl', 'None')}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            
            async with session.post(call_data_url, json=payload) as resp:
                print(f"📊 Response status: {resp.status}")
                
                if resp.status < 400:
                    response_data = await resp.json()
                    print(f"✅ Call-data upload successful!")
                    print(f"📄 Response: {json.dumps(response_data, indent=2)}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Call-data upload failed: {error_text}")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Call-data upload timeout")
        return False
    except Exception as e:
        print(f"❌ Call-data upload error: {e}")
        return False

async def main():
    print("=" * 60)
    print("ACTUAL RECORDING & CRM UPLOAD TEST")
    print("=" * 60)
    
    # Step 1: Upload recording file
    print("🎵 STEP 1: Upload recording file")
    recording_url = await test_recording_upload()
    
    # Step 2: Upload call data
    print(f"\n📊 STEP 2: Upload call data")
    success = await test_call_data_upload(recording_url)
    
    print(f"\n{'✅' if success else '❌'} Overall result: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())