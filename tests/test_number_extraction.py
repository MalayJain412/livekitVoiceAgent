#!/usr/bin/env python3
"""
Test script for number extraction functionality.
Tests the _extract_number_from_sip_uri function and mocks the room inspection.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cagent import _extract_number_from_sip_uri


def test_extract_number_from_sip_uri():
    """Test the number extraction from SIP URI."""
    test_cases = [
        # (input, expected_output)
        ("sip:+916232155888@domain.com", "916232155888"),
        ("sip:916232155888@domain.com", "916232155888"),
        ("sip:+1234567890", "1234567890"),
        ("sip:1234567890", "1234567890"),
        ("+916232155888", "916232155888"),
        ("916232155888", "916232155888"),
        ("invalid", None),
        ("sip:invalid@domain", None),
        ("", None),
    ]

    print("Testing _extract_number_from_sip_uri function:")
    print("=" * 50)

    all_passed = True
    for i, (input_uri, expected) in enumerate(test_cases, 1):
        result = _extract_number_from_sip_uri(input_uri)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print("2d")

    print("=" * 50)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    return all_passed


class MockParticipant:
    """Mock participant for testing."""
    def __init__(self, identity, attributes=None):
        self.identity = identity
        self.attributes = attributes or {}


class MockParticipantsResponse:
    """Mock response for list_participants."""
    def __init__(self, participants):
        self.participants = participants


class MockRoom:
    """Mock room for testing."""
    def __init__(self, name):
        self.name = name


class MockConnection:
    """Mock connection."""
    pass


class MockJobContext:
    """Mock JobContext for testing."""
    def __init__(self, room_name="test-room", participants=None):
        self.room = MockRoom(room_name)
        self.room.connection = MockConnection()
        self.mock_participants = participants or []

    async def mock_list_participants(self, room_name):
        """Mock the list_participants call."""
        return MockParticipantsResponse(self.mock_participants)


async def test_get_sip_participant_and_number():
    """Test the full number extraction with mocked room."""
    print("\nTesting get_sip_participant_and_number with mocked room:")
    print("=" * 50)

    # Mock the room_service to use our mock
    import cagent
    original_room_service = cagent.room_service
    cagent.room_service = type('MockRoomService', (), {
        'RoomServiceClient': lambda conn: type('MockClient', (), {
            'list_participants': lambda self, room_name: asyncio.create_task(mock_list_participants(room_name))
        })()
    })()

    async def mock_list_participants(room_name):
        return MockParticipantsResponse([
            MockParticipant("user_123", {"lk_sip_to": "sip:+916232155888@domain.com"}),
            MockParticipant("sip_+916232155888", {"lk_sip_to": "sip:+916232155888@domain.com"}),
        ])

    # Test case 1: SIP participant with attributes
    ctx = MockJobContext(participants=[
        MockParticipant("user_123"),
        MockParticipant("sip_+916232155888", {"lk_sip_to": "sip:+916232155888@domain.com"}),
    ])

    # We can't easily mock the async function without more setup
    # For now, just test the URI extraction which is the core logic
    print("Note: Full room inspection test requires LiveKit server connection.")
    print("The core extraction logic is tested above.")

    # Restore original
    cagent.room_service = original_room_service


def main():
    """Run all tests."""
    print("Number Extraction Test Suite")
    print("=" * 50)

    # Test URI extraction
    uri_test_passed = test_extract_number_from_sip_uri()

    # Test full function (mocked)
    asyncio.run(test_get_sip_participant_and_number())

    print("\n" + "=" * 50)
    if uri_test_passed:
        print("✅ Core number extraction logic is working correctly!")
        print("The function should properly extract numbers from SIP URIs.")
    else:
        print("❌ Core number extraction has issues.")

    print("\nTo test the full room inspection:")
    print("1. Start the LiveKit server")
    print("2. Make a test SIP call")
    print("3. Check the agent logs for 'Extracted dialed number: <number>'")


if __name__ == "__main__":
    main()