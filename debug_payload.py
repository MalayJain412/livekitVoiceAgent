#!/usr/bin/env python3
"""
Debug the CRM upload payload to see what's causing the 400 error
"""

import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_payload_structure():
    """Debug what payload is being sent to CRM"""
    
    # Load a real transcript file
    conversations_path = Path("conversations")
    transcript_files = list(conversations_path.glob("transcript_session_*.json"))
    
    if not transcript_files:
        print("❌ No transcript files found")
        return
    
    # Get the most recent file
    transcript_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    recent_file = transcript_files[0]
    
    print(f"📁 Analyzing: {recent_file.name}")
    
    # Load transcript data
    with open(recent_file, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    print(f"\n📊 Transcript data structure:")
    print(f"  Keys: {list(transcript_data.keys())}")
    
    # Simulate the payload building from crm_upload.py
    campaign_id = "68c91223fde0aa95caa3dbe4"
    voice_agent_id = "68c9105cfde0aa95caa3db64"
    client_id = "68c90d626052ee95ac77059d"
    caller_phone = "+918655200389"
    call_id = f"DEBUG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Extract timing information like crm_upload.py does
    start_time = None
    end_time = None
    
    items = transcript_data.get("items", [])
    
    # Try to extract timing from items
    for item in items:
        if isinstance(item, dict) and "timestamp" in item:
            timestamp_str = item["timestamp"]
            try:
                # Try parsing different timestamp formats
                if timestamp_str.endswith('Z'):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
                
                if start_time is None or timestamp < start_time:
                    start_time = timestamp
                if end_time is None or timestamp > end_time:
                    end_time = timestamp
            except Exception as e:
                print(f"  ⚠️ Failed to parse timestamp '{timestamp_str}': {e}")
    
    # Use session-level timestamps if item-level parsing failed
    if not start_time and "start_time" in transcript_data:
        try:
            start_time = datetime.fromisoformat(str(transcript_data["start_time"]).replace('Z', '+00:00'))
        except:
            start_time = datetime.now()
    
    if not end_time and "end_time" in transcript_data:
        try:
            end_time = datetime.fromisoformat(str(transcript_data["end_time"]).replace('Z', '+00:00'))
        except:
            end_time = start_time
    
    if not start_time:
        start_time = datetime.now()
    if not end_time:
        end_time = start_time
    
    duration = int((end_time - start_time).total_seconds()) if end_time and start_time else 0
    
    # Build the payload that would be sent to CRM
    payload = {
        "campaignId": campaign_id,
        "voiceAgentId": voice_agent_id,
        "client": client_id,
        "callDetails": {
            "callId": call_id,
            "direction": "outbound",
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "duration": duration,
            "phoneNumber": caller_phone
        },
        "caller": {
            "phoneNumber": caller_phone
        },
        "transcription": {
            "text": " ".join([
                item.get("content", "") for item in items 
                if isinstance(item, dict) and item.get("content")
            ]) or "No transcription available",
            "events": [
                {
                    "timestamp": item.get("timestamp", ""),
                    "speaker": item.get("role", "unknown"),
                    "text": item.get("content", "")
                }
                for item in items
                if isinstance(item, dict) and item.get("content")
            ]
        },
        "lead": {}  # No lead data in this file
    }
    
    print(f"\n📤 CRM Payload that would be sent:")
    print(json.dumps(payload, indent=2, default=str))
    
    print(f"\n🔍 Payload validation:")
    print(f"  - campaignId: {'✅' if payload['campaignId'] else '❌'}")
    print(f"  - voiceAgentId: {'✅' if payload['voiceAgentId'] else '❌'}")
    print(f"  - client: {'✅' if payload['client'] else '❌'}")
    print(f"  - callId: {'✅' if payload['callDetails']['callId'] else '❌'}")
    print(f"  - phoneNumber: {'✅' if payload['caller']['phoneNumber'] else '❌'}")
    print(f"  - transcription events: {len(payload['transcription']['events'])}")
    
    # Check for potential issues
    issues = []
    if not payload['transcription']['events']:
        issues.append("No transcription events")
    if duration <= 0:
        issues.append("Zero duration")
    if not payload['transcription']['text'].strip():
        issues.append("Empty transcription text")
    
    if issues:
        print(f"\n⚠️ Potential issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ Payload looks valid")

if __name__ == "__main__":
    print("=" * 60)
    print("DEBUGGING CRM UPLOAD PAYLOAD")
    print("=" * 60)
    
    debug_payload_structure()
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)