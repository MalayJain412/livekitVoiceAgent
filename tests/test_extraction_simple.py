#!/usr/bin/env python3
"""
Simple test script for number extraction from SIP URIs.
Tests only the core extraction logic without heavy dependencies.
"""

def extract_number_from_sip_uri(uri: str):
    """Extract phone number from SIP URI format or participant identity."""
    try:
        # Handle participant identity format: sip_+1234567890
        if uri.startswith("sip_"):
            # Remove sip_ prefix
            uri = uri[4:]
            
            # Remove + if present
            if uri.startswith("+"):
                uri = uri[1:]
            
            # Should be digits only
            if uri.isdigit():
                return uri
        
        # Handle sip:+1234567890@domain format
        if uri.startswith("sip:"):
            # Remove sip: prefix
            uri = uri[4:]
            
            # Remove @domain part
            if "@" in uri:
                uri = uri.split("@")[0]
            
            # Remove + if present
            if uri.startswith("+"):
                uri = uri[1:]
            
            # Should be digits only
            if uri.isdigit():
                return uri
        
        return None
    except Exception as e:
        print(f"Error extracting number from URI {uri}: {e}")
        return None
def test_extract_number_from_sip_uri():
    """Test the number extraction from SIP URI."""
    test_cases = [
        # (input, expected_output)
        ("sip:+916232155888@domain.com", "916232155888"),
        ("sip:916232155888@domain.com", "916232155888"),
        ("sip:+1234567890", "1234567890"),
        ("sip:1234567890", "1234567890"),
        ("+916232155888", None),  # No sip prefix
        ("916232155888", None),   # No sip prefix
        ("sip_+916232155888", "916232155888"),  # Participant identity
        ("sip_916232155888", "916232155888"),   # Participant identity without +
        ("invalid", None),
        ("sip:invalid@domain", None),
        ("", None),
    ]

    print("Testing extract_number_from_sip_uri function:")
    print("=" * 60)

    all_passed = True
    for i, (input_uri, expected) in enumerate(test_cases, 1):
        result = extract_number_from_sip_uri(input_uri)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print("2d")

    print("=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("The number extraction logic is working correctly.")
    else:
        print("❌ Some tests failed!")
    return all_passed


def test_real_world_examples():
    """Test with real-world examples from the logs."""
    print("\nTesting with real-world examples from LiveKit logs:")
    print("=" * 60)

    examples = [
        "sip_+916232155888",  # Participant identity from logs
        "sip:+916232155888@20.193.141.77",  # Potential SIP URI
        "+916232155888",  # Clean number
    ]

    for example in examples:
        result = extract_number_from_sip_uri(example)
        print(f"Input: '{example}' -> Extracted: {result}")


def main():
    """Run all tests."""
    print("Number Extraction Test Suite")
    print("=" * 60)
    print("This tests the core logic for extracting phone numbers from SIP URIs.")
    print("Used in the voice agent to identify which number was dialed.")
    print()

    # Test URI extraction
    uri_test_passed = test_extract_number_from_sip_uri()

    # Test real examples
    test_real_world_examples()

    print("\n" + "=" * 60)
    if uri_test_passed:
        print("✅ Core number extraction logic is working correctly!")
        print("The agent should be able to extract dialed numbers from SIP calls.")
        print("\nNext steps:")
        print("1. Update the SIP dispatch rule on the server with the agent config")
        print("2. Test with a real SIP call to verify the full flow")
    else:
        print("❌ Core number extraction has issues that need to be fixed.")


if __name__ == "__main__":
    main()