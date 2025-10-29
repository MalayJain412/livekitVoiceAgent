#!/usr/bin/env python3
"""
Analyze conversation structure and test CRM upload with proper payload
"""
import json
import asyncio
import aiohttp
from datetime import datetime

def analyze_conversation(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📄 File: {file_path}")
    print(f"🔑 Keys: {list(data.keys())}")
    print(f"📊 Items count: {len(data.get('items', []))}")
    print(f"⏱️  Duration: {data.get('duration_seconds')} seconds")
    print(f"🆔 Session ID: {data.get('session_id')}")
    print(f"🏁 Lead generated: {data.get('lead_generated', False)}")
    
    print("\n📝 Conversation items:")
    for i, item in enumerate(data['items'][:8]):  # Show first 8 items
        role = item.get('role') or item.get('type') or 'unknown'
        content = str(item.get('content', ''))[:80] + ('...' if len(str(item.get('content', ''))) > 80 else '')
        timestamp = item.get('timestamp', '')
        source = item.get('source', '')
        print(f"  {i+1}. [{role}] {content} | {timestamp} | {source}")
    
    if len(data['items']) > 8:
        print(f"  ... and {len(data['items']) - 8} more items")
    
    return data

def build_proper_payload(conv_data, campaign_id, voice_agent_id, client_id, caller_number, recording_url=None):
    """Build CRM payload using the exact structure you provided"""
    
    # Extract conversation items in the proper format
    conversation_items = []
    for item in conv_data.get('items', []):
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
    
    # Build the payload in your exact format
    start_time = conv_data.get('start_time', '')
    end_time = conv_data.get('end_time', '')
    duration = int(conv_data.get('duration_seconds', 0))
    
    # Parse timestamps
    try:
        if 'T' not in start_time:
            start_time = start_time.replace(' ', 'T').replace('+00:00', 'Z')
        if 'T' not in end_time:
            end_time = end_time.replace(' ', 'T').replace('+00:00', 'Z')
    except:
        pass
    
    # Generate call ID from session
    session_id = conv_data.get('session_id', '')
    call_id = f"CALL-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{session_id[-8:] if session_id else 'unknown'}"
    
    payload = {
        "campaignId": campaign_id,
        "voiceAgentId": voice_agent_id,
        "client": client_id,
        "callDetails": {
            "callId": call_id,
            "direction": "inbound",
            "startTime": start_time,
            "endTime": end_time,
            "duration": duration,
            "status": "completed",
            "callerNumber": caller_number,
            "recordingUrl": recording_url,
            "recordingDuration": duration,
            "recordingSize": None  # Will be filled if we have it
        },
        "caller": {
            "phoneNumber": caller_number
        },
        "transcription": {
            "session_id": conv_data.get('session_id'),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": conv_data.get('duration_seconds'),
            "total_items": len(conversation_items),
            "conversation_items": conversation_items,
            "lead_generated": conv_data.get('lead_generated', False),
            "metadata": conv_data.get('metadata', {})
        },
        "lead": conv_data.get('lead', {})
    }
    
    return payload

async def test_crm_upload(payload):
    """Test uploading the payload to CRM"""
    url = "https://devcrm.xeny.ai/apis/api/public/call-data"
    
    print(f"\n🚀 Testing CRM upload to: {url}")
    print(f"📦 Payload size: {len(json.dumps(payload))} characters")
    print(f"🎯 Call ID: {payload['callDetails']['callId']}")
    print(f"📊 Conversation items: {len(payload['transcription']['conversation_items'])}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(url, json=payload) as resp:
                print(f"📈 Response status: {resp.status}")
                
                if resp.status < 400:
                    response_data = await resp.json()
                    print(f"✅ Upload successful!")
                    print(f"📄 Response: {json.dumps(response_data, indent=2)}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Upload failed")
                    print(f"📄 Error response: {error_text}")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Upload timeout (30s)")
        return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

async def main():
    print("=" * 60)
    print("CONVERSATION ANALYSIS & CRM UPLOAD TEST")
    print("=" * 60)
    
    # Analyze the conversation file
    conv_file = "conversations/transcript_session_2025-10-23T07-56-34.738476.json"
    conv_data = analyze_conversation(conv_file)
    
    # Build the proper payload
    print(f"\n🔧 Building CRM payload...")
    payload = build_proper_payload(
        conv_data,
        campaign_id="68c91223fde0aa95caa3dbe4",
        voice_agent_id="68c9105cfde0aa95caa3db64", 
        client_id="68c90d626052ee95ac77059d",
        caller_number="+919876543210",
        recording_url="https://devcrm.xeny.ai/apis/uploads/recordings/1761646722349.ogg"
    )
    
    print(f"✅ Payload built successfully")
    print(f"📋 Sample conversation items:")
    for i, item in enumerate(payload['transcription']['conversation_items'][:3]):
        print(f"  {i+1}. [{item['role']}] {item['content'][:60]}...")
    
    # Test the upload
    success = await test_crm_upload(payload)
    
    print(f"\n{'✅' if success else '❌'} Overall result: {'SUCCESS' if success else 'FAILED'}")
    
    # Save payload for inspection
    with open('test_payload.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"💾 Payload saved to: test_payload.json")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())