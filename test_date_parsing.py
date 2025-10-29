#!/usr/bin/env python3
"""
Test date parsing for CRM upload
"""
import json
import os
from datetime import datetime

def test_date_parsing():
    print("=" * 50)
    print("TESTING DATE PARSING FOR CRM UPLOAD")
    print("=" * 50)
    
    # Load a conversation file to get real timestamp formats
    conv_file = "conversations/transcript_session_2025-10-28T06-28-25.034382.json"
    if not os.path.exists(conv_file):
        print("❌ Test conversation file not found")
        return
    
    with open(conv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    start_time = data.get('start_time', '')
    end_time = data.get('end_time', '')
    
    print(f"📄 Original start_time: {start_time}")
    print(f"📄 Original end_time: {end_time}")
    print(f"🔍 Start type: {type(start_time)}")
    print(f"🔍 End type: {type(end_time)}")
    
    # Test the parsing logic
    def parse_timestamp(timestamp):
        """Test the timestamp parsing logic"""
        try:
            if timestamp:
                if isinstance(timestamp, str):
                    # Handle format: "2025-10-28 06:27:29.508221+00:00"
                    if ' ' in timestamp and '+' in timestamp:
                        # Replace space with T and ensure Z ending
                        timestamp = timestamp.replace(' ', 'T').replace('+00:00', 'Z')
                    elif 'T' in timestamp and not timestamp.endswith('Z'):
                        # Ensure Z ending for UTC
                        timestamp = timestamp.rstrip('Z') + 'Z'
            return timestamp
        except Exception as e:
            print(f"❌ Error parsing timestamp: {e}")
            return datetime.utcnow().isoformat() + "Z"
    
    parsed_start = parse_timestamp(start_time)
    parsed_end = parse_timestamp(end_time)
    
    print(f"\n✅ Parsed start_time: {parsed_start}")
    print(f"✅ Parsed end_time: {parsed_end}")
    
    # Validate the format
    try:
        # Try to parse with datetime to validate format
        datetime.fromisoformat(parsed_start.replace('Z', '+00:00'))
        datetime.fromisoformat(parsed_end.replace('Z', '+00:00'))
        print("\n🎉 Timestamps are valid ISO format!")
        return True
    except Exception as e:
        print(f"\n❌ Invalid timestamp format: {e}")
        return False

if __name__ == "__main__":
    success = test_date_parsing()
    print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")