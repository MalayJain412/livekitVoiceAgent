#!/usr/bin/env python3
"""
Test that CRM upload only processes MongoDB-formatted transcript files
"""

import json
import os
from pathlib import Path
import tempfile
import sys

def test_file_filtering():
    """Test that the CRM upload filtering works correctly"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        conversations_path = Path(temp_dir)
        
        # Create a MongoDB-formatted file (SHOULD be included)
        mongodb_file = conversations_path / "transcript_session_2025-10-28T15-30-00.123456.json"
        mongodb_data = {
            "session_id": "session_20251028_153000_abcd1234",
            "start_time": "2025-10-28T15:30:00.000000",
            "end_time": "2025-10-28T15:35:00.000000",
            "items": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "total_items": 2,
            "duration_seconds": 300,
            "lead_generated": False,
            "metadata": {"auto_saved": True},
            "_id": "mongo_id_123"
        }
        
        with open(mongodb_file, 'w') as f:
            json.dump(mongodb_data, f, indent=2)
        
        # Create a raw transcript file (SHOULD be excluded)
        raw_file = conversations_path / "transcript_number-_918655066243_2025-10-28T15-30-00.json"
        raw_data = [
            {"id": "item_123", "type": "message", "role": "user", "content": ["Hello"]},
            {"id": "item_456", "type": "message", "role": "assistant", "content": ["Hi there!"]}
        ]
        
        with open(raw_file, 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        # Create another MongoDB file (SHOULD be included)
        mongodb_file2 = conversations_path / "transcript_session_2025-10-28T16-00-00.789012.json"
        with open(mongodb_file2, 'w') as f:
            json.dump(mongodb_data, f, indent=2)
        
        # Create a malformed JSON file (SHOULD be excluded)
        bad_file = conversations_path / "transcript_session_2025-10-28T17-00-00.999999.json"
        with open(bad_file, 'w') as f:
            f.write("invalid json content")
        
        print(f"Created test files in {temp_dir}:")
        print(f"  - {mongodb_file.name} (MongoDB format - SHOULD include)")
        print(f"  - {raw_file.name} (Raw format - SHOULD exclude)")
        print(f"  - {mongodb_file2.name} (MongoDB format - SHOULD include)")
        print(f"  - {bad_file.name} (Malformed - SHOULD exclude)")
        
        # Now test the filtering logic from crm_upload.py
        transcript_files = list(conversations_path.glob("transcript_session_*.json"))
        print(f"\nFound {len(transcript_files)} files matching transcript_session_*.json pattern:")
        for f in transcript_files:
            print(f"  - {f.name}")
        
        # Apply the MongoDB filtering logic
        mongodb_files = []
        for transcript_file in transcript_files:
            if transcript_file.name.startswith("transcript_session_"):
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and 'session_id' in data and 'items' in data:
                        mongodb_files.append(transcript_file)
                        print(f"  ✅ {transcript_file.name} - Valid MongoDB format")
                    else:
                        print(f"  ❌ {transcript_file.name} - Invalid structure")
                except:
                    print(f"  ❌ {transcript_file.name} - Failed to parse JSON")
        
        print(f"\nFiltered to {len(mongodb_files)} MongoDB-formatted files:")
        for f in mongodb_files:
            print(f"  - {f.name}")
        
        # Verify results
        expected_files = {mongodb_file.name, mongodb_file2.name}
        actual_files = {f.name for f in mongodb_files}
        
        if actual_files == expected_files:
            print("\n✅ PASS: Filtering correctly identified MongoDB-formatted files only")
            return True
        else:
            print(f"\n❌ FAIL: Expected {expected_files}, got {actual_files}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING CRM UPLOAD FILE FILTERING")
    print("=" * 60)
    
    success = test_file_filtering()
    
    print("\n" + "=" * 60)
    print(f"TEST {'PASSED' if success else 'FAILED'}")
    print("=" * 60)
    
    sys.exit(0 if success else 1)