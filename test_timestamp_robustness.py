#!/usr/bin/env python3
"""
Test various timestamp formats for CRM upload robustness
"""
from datetime import datetime

def test_timestamp_formats():
    print("=" * 60)
    print("TESTING VARIOUS TIMESTAMP FORMATS")
    print("=" * 60)
    
    # Test cases with different timestamp formats
    test_cases = [
        ("2025-10-28 06:27:29.508221+00:00", "Space with timezone"),
        ("2025-10-28T06:27:29.508221Z", "ISO format with Z"),
        ("2025-10-28T06:27:29.508221", "ISO format without Z"),
        ("2025-10-28T06:27:29+00:00", "ISO format with timezone"),
        ("", "Empty string"),
        (None, "None value"),
    ]
    
    def parse_timestamp(timestamp):
        """Robust timestamp parsing logic"""
        try:
            if not timestamp:
                return datetime.utcnow().isoformat() + "Z"
                
            if isinstance(timestamp, str):
                # Handle format: "2025-10-28 06:27:29.508221+00:00"
                if ' ' in timestamp and '+' in timestamp:
                    # Replace space with T and ensure Z ending
                    timestamp = timestamp.replace(' ', 'T').replace('+00:00', 'Z')
                elif 'T' in timestamp and timestamp.endswith('+00:00'):
                    # Replace timezone with Z
                    timestamp = timestamp.replace('+00:00', 'Z')
                elif 'T' in timestamp and not timestamp.endswith('Z'):
                    # Ensure Z ending for UTC
                    timestamp = timestamp.rstrip('Z') + 'Z'
                    
            return timestamp
        except Exception as e:
            print(f"❌ Error parsing timestamp: {e}")
            return datetime.utcnow().isoformat() + "Z"
    
    all_passed = True
    
    for i, (test_input, description) in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {description}")
        print(f"   Input: {repr(test_input)}")
        
        try:
            parsed = parse_timestamp(test_input)
            print(f"   Output: {parsed}")
            
            # Validate the result
            if parsed:
                # Try to parse as datetime to validate
                datetime.fromisoformat(parsed.replace('Z', '+00:00'))
                print(f"   ✅ Valid ISO format")
            else:
                print(f"   ❌ Empty result")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            all_passed = False
    
    print(f"\n" + "=" * 60)
    print(f"RESULT: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    test_timestamp_formats()