#!/usr/bin/env python3
"""Quick test script for hangup phrase detection."""

from session_manager import HANGUP_PHRASES

def test_hangup_detection():
    print("Configured hangup phrases:")
    for i, phrase in enumerate(HANGUP_PHRASES):
        print(f"  {i+1:2d}. '{phrase}'")
    print()
    
    # Test cases from the call log
    test_cases = [
        "Hello?",
        "Sorry. I just made a wrong call.",
        "Just can you please sign the call?",
        "please hang up the call",
        "hang up",
        "goodbye",
        "bye bye",
        "please disconnect"
    ]
    
    for test_text in test_cases:
        print(f"Testing: '{test_text}'")
        user_text = test_text.strip().lower()
        matched_phrase = None
        
        for phrase in HANGUP_PHRASES:
            if phrase in user_text:
                matched_phrase = phrase
                break
        
        if matched_phrase:
            print(f"  ✓ MATCH: '{matched_phrase}' found in text")
        else:
            print(f"  ✗ NO MATCH found")
        print()

if __name__ == "__main__":
    test_hangup_detection()