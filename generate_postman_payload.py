#!/usr/bin/env python3
"""
Generate example payload for Postman testing
"""
import json
import os
from datetime import datetime

def generate_postman_payload():
    print("=" * 60)
    print("GENERATING POSTMAN PAYLOAD EXAMPLE")
    print("=" * 60)
    
    # Load a real conversation file
    conv_file = "conversations/transcript_session_2025-10-28T06-28-25.034382.json"
    if not os.path.exists(conv_file):
        print("❌ Conversation file not found")
        return
    
    with open(conv_file, 'r', encoding='utf-8') as f:
        conversation_data = json.load(f)
    
    # Extract conversation items for the payload
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
    
    # Parse timestamps
    start_time = conversation_data.get('start_time', '')
    end_time = conversation_data.get('end_time', '')
    
    # Convert to proper ISO format
    if ' ' in start_time and '+' in start_time:
        start_time = start_time.replace(' ', 'T').replace('+00:00', 'Z')
    if ' ' in end_time and '+' in end_time:
        end_time = end_time.replace(' ', 'T').replace('+00:00', 'Z')
    
    # Generate call ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = conversation_data.get('session_id', 'unknown')
    call_id = f"CALL-{timestamp}-{session_id[-8:] if session_id else 'postman'}"
    
    # Build the complete payload
    payload = {
        "campaignId": "68c91223fde0aa95caa3dbe4",
        "voiceAgentId": "68c9105cfde0aa95caa3db64",
        "client": "68c90d626052ee95ac77059d",
        "callDetails": {
            "callId": call_id,
            "direction": "inbound",
            "startTime": start_time,
            "endTime": end_time,
            "duration": int(conversation_data.get('duration_seconds', 0)),
            "status": "completed",
            "callerNumber": "+919876543210",
            "recordingUrl": "https://devcrm.xeny.ai/apis/uploads/recordings/1761646722349.ogg",
            "recordingDuration": int(conversation_data.get('duration_seconds', 0)),
            "recordingSize": 2048000
        },
        "caller": {
            "phoneNumber": "+919876543210"
        },
        "transcription": {
            "session_id": conversation_data.get('session_id'),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": conversation_data.get('duration_seconds'),
            "total_items": len(conversation_items),
            "conversation_items": conversation_items,
            "lead_generated": conversation_data.get('lead_generated', False),
            "metadata": conversation_data.get('metadata', {
                "language": "hi-IN",
                "channel": "voice",
                "source": "friday-ai-assistant"
            })
        },
        "lead": conversation_data.get('lead', {})
    }
    
    # Save the payload
    payload_file = "postman_payload_example.json"
    with open(payload_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Payload generated successfully!")
    print(f"📁 Saved to: {payload_file}")
    print(f"🎯 Call ID: {call_id}")
    print(f"📊 Conversation items: {len(conversation_items)}")
    print(f"📋 Payload size: {len(json.dumps(payload))} characters")
    
    # Print Postman instructions
    print("\n" + "=" * 60)
    print("POSTMAN SETUP INSTRUCTIONS")
    print("=" * 60)
    print("1. Method: POST")
    print("2. URL: https://devcrm.xeny.ai/apis/api/public/call-data")
    print("3. Headers:")
    print("   - Content-Type: application/json")
    print("4. Body: Raw JSON (copy from postman_payload_example.json)")
    print("5. Expected Response: 201 Created with call processing details")
    
    return payload

if __name__ == "__main__":
    generate_postman_payload()