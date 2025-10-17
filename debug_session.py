#!/usr/bin/env python3
"""
Debug script to test session_manager hangup detection
"""
import sys
import os
import json
import re
from datetime import datetime
sys.path.append(os.getcwd())

from session_manager import HANGUP_PHRASES

def test_transcript_parsing():
    """Test parsing the actual transcript to see what we extract"""
    transcript_path = "conversations/transcript_session_2025-10-17T10-54-36.988248.json"
    
    if not os.path.exists(transcript_path):
        print(f"Transcript file not found: {transcript_path}")
        return
    
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== ANALYZING TRANSCRIPT ===")
    print(f"Session ID: {data.get('session_id')}")
    print(f"Total items: {data.get('total_items')}")
    print()
    
    for item in data.get('items', []):
        role = item.get('role', '')
        content = item.get('content', '')
        source = item.get('source', '')
        raw = item.get('raw', '')
        
        print(f"Item: role={role}, source={source}")
        
        if content:
            print(f"  Content: '{content}'")
        
        if raw and role == "unknown":
            # Test our raw parsing logic
            try:
                # extract role from raw
                mrole = re.search(r"role='([^']+)'", str(raw))
                extracted_role = mrole.group(1) if mrole else None
                
                # extract content from raw
                m = re.search(r"content=\[(.*)\]", str(raw))
                extracted_content = ""
                if m:
                    raw_content = m.group(1).strip()
                    if raw_content.startswith("'") and raw_content.endswith("'"):
                        raw_content = raw_content[1:-1]
                    extracted_content = raw_content
                
                print(f"  Raw role: {extracted_role}")
                print(f"  Raw content: '{extracted_content}'")
                
                # Test hangup detection
                if extracted_role == "user" and extracted_content:
                    user_text = extracted_content.lower()
                    print(f"  Testing hangup detection on: '{user_text}'")
                    
                    matched_phrases = []
                    for phrase in HANGUP_PHRASES:
                        if phrase in user_text:
                            matched_phrases.append(phrase)
                    
                    if matched_phrases:
                        print(f"  *** HANGUP DETECTED! Matched phrases: {matched_phrases}")
                    else:
                        print(f"  No hangup phrases found")
                        
            except Exception as e:
                print(f"  Error parsing raw: {e}")
        
        print()

if __name__ == "__main__":
    test_transcript_parsing()