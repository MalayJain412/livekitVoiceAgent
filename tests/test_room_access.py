#!/usr/bin/env python3
"""
Test script to verify room participant access in LiveKit agents.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the LiveKit components for testing
class MockParticipant:
    def __init__(self, identity, attributes=None):
        self.identity = identity
        self.attributes = attributes or {}

class MockRoom:
    def __init__(self, participants_dict, room_name="test-room"):
        self.participants = participants_dict
        self.name = room_name

class MockJobContext:
    def __init__(self, participants_dict, room_name="test-room"):
        self.room = MockRoom(participants_dict, room_name)

# Import the function after setting up mocks
from cagent import get_sip_participant_and_number, _extract_number_from_sip_uri

async def test_room_participant_access():
    """Test accessing participants through room object."""
    print("Testing room participant access:")
    print("=" * 50)

    # Test 1: Participants available
    participants = {
        "user_123": MockParticipant("user_123"),
        "sip_+916232155888": MockParticipant("sip_+916232155888", {"lk_sip_to": "sip:+918655054859@domain.com"}),
    }

    ctx = MockJobContext(participants)

    try:
        participant_identity, dialed_number = await get_sip_participant_and_number(ctx)

        print(f"Test 1 - Participants available:")
        print(f"  Participant Identity: {participant_identity}")
        print(f"  Extracted Number: {dialed_number}")

        if participant_identity == "sip_+916232155888" and dialed_number == "918655054859":
            print("  ✅ Participants test passed!")
        else:
            print("  ❌ Participants test failed - wrong values returned")
            return False

    except Exception as e:
        print(f"❌ Participants test failed with error: {e}")
        return False

    # Test 2: No participants, fallback to room name
    print(f"\nTest 2 - Room name fallback:")
    ctx2 = MockJobContext({}, "friday-call-_+916232155888_8ebDVBAxK95T")

    try:
        participant_identity, dialed_number = await get_sip_participant_and_number(ctx2)

        print(f"  Room Name: {ctx2.room.name}")
        print(f"  Participant Identity: {participant_identity}")
        print(f"  Extracted Number: {dialed_number}")

        if dialed_number == "918655054859":  # Now returns the dialed number
            print("  ✅ Room name fallback test passed!")
            return True
        else:
            print("  ❌ Room name fallback test failed")
            return False
    except Exception as e:
        print(f"❌ Room name fallback test failed with error: {e}")
        return False

def test_number_extraction():
    """Test the number extraction logic."""
    print("\nTesting number extraction:")
    print("=" * 50)

    test_cases = [
        ("sip_+916232155888", "916232155888"),
        ("sip:+918655054859@domain.com", "918655054859"),
        ("sip:918655054859@domain.com", "918655054859"),
        ("+916232155888", "916232155888"),
        ("916232155888", "916232155888"),
    ]

    all_passed = True
    for identity, expected in test_cases:
        result = _extract_number_from_sip_uri(identity)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print(f"Input: '{identity}' -> Expected: {expected}, Got: {result} [{status}]")

    if all_passed:
        print("✅ Number extraction tests passed!")
    else:
        print("❌ Number extraction tests failed!")

    return all_passed

async def main():
    """Run all tests."""
    print("Room Access Test Suite")
    print("=" * 50)

    # Test number extraction
    extraction_passed = test_number_extraction()

    # Test room access
    room_access_passed = await test_room_participant_access()

    print("\n" + "=" * 50)
    if extraction_passed and room_access_passed:
        print("✅ All tests passed!")
        print("The agent should now be able to extract dialed numbers from room participants.")
    else:
        print("❌ Some tests failed.")
        if not extraction_passed:
            print("  - Number extraction logic has issues")
        if not room_access_passed:
            print("  - Room participant access has issues")

if __name__ == "__main__":
    asyncio.run(main())