#!/usr/bin/env python3
"""
Test CRM upload with a real MongoDB-formatted transcript file
"""

import asyncio
import json
from pathlib import Path
import sys
import os

# Add current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crm_upload import upload_from_transcript_file

async def test_real_transcript_upload():
    """Test uploading a real MongoDB-formatted transcript file"""
    
    # Find the most recent MongoDB-formatted transcript file
    conversations_path = Path("conversations")
    transcript_files = list(conversations_path.glob("transcript_session_*.json"))
    
    if not transcript_files:
        print("❌ No MongoDB-formatted transcript files found")
        return False
    
    # Sort by modification time and get the most recent
    transcript_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    recent_file = transcript_files[0]
    
    print(f"📁 Testing with file: {recent_file.name}")
    
    # Check file structure
    try:
        with open(recent_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 File structure:")
        print(f"  - Session ID: {data.get('session_id', 'missing')}")
        print(f"  - Total items: {data.get('total_items', 0)}")
        print(f"  - Duration: {data.get('duration_seconds', 0)} seconds")
        print(f"  - Lead generated: {data.get('lead_generated', False)}")
        
        if not isinstance(data, dict) or 'session_id' not in data or 'items' not in data:
            print("❌ File does not have proper MongoDB format")
            return False
        
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return False
    
    # Test CRM upload (dry run first)
    print(f"\n🧪 Testing CRM upload...")
    
    # Use test credentials from persona handler
    campaign_id = "68c91223fde0aa95caa3dbe4"
    voice_agent_id = "68c9105cfde0aa95caa3db64"  
    client_id = "68c90d626052ee95ac77059d"
    
    # Extract phone from session data or use test number
    caller_phone = "+918655200389"  # Default test number
    
    try:
        # Generate a test call ID
        from datetime import datetime
        call_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}-UPLOAD"
        
        print(f"📤 Attempting upload with:")
        print(f"  - Campaign ID: {campaign_id}")
        print(f"  - Voice Agent ID: {voice_agent_id}")
        print(f"  - Client ID: {client_id}")
        print(f"  - Call ID: {call_id}")
        print(f"  - Caller: {caller_phone}")
        
        # Call the upload function
        success = upload_from_transcript_file(
            transcript_file_path=str(recent_file),
            campaign_id=campaign_id,
            voice_agent_id=voice_agent_id,
            client_id=client_id,
            caller_phone=caller_phone,
            call_id=call_id,
            lead_file_path=None  # No lead file for this test
        )
        
        if success:
            print("✅ CRM upload successful!")
            return True
        else:
            print("❌ CRM upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

async def main():
    print("=" * 60)
    print("TESTING REAL TRANSCRIPT FILE CRM UPLOAD")
    print("=" * 60)
    
    success = await test_real_transcript_upload()
    
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)