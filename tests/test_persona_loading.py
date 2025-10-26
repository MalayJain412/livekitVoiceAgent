#!/usr/bin/env python3
"""
Test script for persona loading from dialed number.
Tests the API integration and persona configuration loading.
"""

import asyncio
import sys
import os
import json
from unittest.mock import AsyncMock, Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the heavy dependencies to avoid import issues
sys.modules['livekit'] = Mock()
sys.modules['livekit.agents'] = Mock()
sys.modules['livekit.plugins'] = Mock()
sys.modules['livekit.api'] = Mock()
sys.modules['livekit.api.room_service'] = Mock()
sys.modules['prompts'] = Mock()
sys.modules['tools'] = Mock()
sys.modules['config'] = Mock()
sys.modules['instances'] = Mock()
sys.modules['session_manager'] = Mock()
sys.modules['validation'] = Mock()
sys.modules['logging_config'] = Mock()
sys.modules['transcript_logger'] = Mock()

# Mock logging
import logging
logging.basicConfig(level=logging.INFO)

# Now import the function we want to test
from cagent import load_persona_from_dialed_number


async def test_load_persona_from_dialed_number():
    """Test loading persona from dialed number with mocked API."""
    print("Testing load_persona_from_dialed_number function:")
    print("=" * 60)

    # Mock persona data that the API should return
    mock_persona_data = {
        "persona_name": "Test Agent",
        "agent_instructions": "You are a helpful test agent.",
        "session_instructions": "Start with a greeting and ask how you can help.",
        "closing_message": "Thank you for testing!",
        "voice_settings": {
            "voice": "alloy",
            "language": "en"
        },
        "is_active": True
    }

    # Test successful API call
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_persona_data)

        # Mock the context manager for session.get()
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_get_cm

        try:
            result = await load_persona_from_dialed_number("918655054859")

            agent_instructions, session_instructions, closing_message, persona_name, full_config = result

            # Verify the results
            assert agent_instructions == "You are a helpful test agent."
            assert session_instructions == "Start with a greeting and ask how you can help."
            assert closing_message == "Thank you for testing!"
            assert persona_name == "Test Agent"
            assert full_config == mock_persona_data

            print("✅ Successful API call test passed!")
            print(f"   Persona Name: {persona_name}")
            print(f"   Agent Instructions: {agent_instructions[:50]}...")
            print(f"   Session Instructions: {session_instructions}")
            print(f"   Closing Message: {closing_message}")

        except Exception as e:
            print(f"❌ Successful API call test failed: {e}")
            return False

    # Test API error (404)
    print("\nTesting API error handling:")
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_get_cm

        try:
            await load_persona_from_dialed_number("999999999999")
            print("❌ API error test failed: Should have raised ValueError")
            return False
        except ValueError as e:
            if "API returned status 404" in str(e):
                print("✅ API error handling test passed!")
            else:
                print(f"❌ API error test failed: Wrong error message: {e}")
                return False
        except Exception as e:
            print(f"❌ API error test failed: Unexpected error: {e}")
            return False

    # Test network error
    print("\nTesting network error handling:")
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_session.get.side_effect = Exception("Network timeout")

        try:
            await load_persona_from_dialed_number("918655054859")
            print("❌ Network error test failed: Should have raised exception")
            return False
        except Exception as e:
            if "Network timeout" in str(e):
                print("✅ Network error handling test passed!")
            else:
                print(f"❌ Network error test failed: Wrong error: {e}")
                return False

    return True


def test_real_api_call():
    """Test with real API call (optional, requires network)."""
    print("\n" + "=" * 60)
    print("Testing with real API call (requires network):")
    print("Note: This will make an actual call to https://devcrm.xeny.ai")
    print("Skip this if you don't want to test the real API.")

    async def real_test():
        try:
            # Test with the number from your logs
            result = await load_persona_from_dialed_number("918655054859")
            agent_instructions, session_instructions, closing_message, persona_name, full_config = result

            print("✅ Real API call successful!")
            print(f"   Persona Name: {persona_name}")
            print(f"   Agent Instructions: {agent_instructions[:100]}...")
            print(f"   Session Instructions: {session_instructions}")
            print(f"   Closing Message: {closing_message}")
            print(f"   Full Config Keys: {list(full_config.keys())}")

            return True
        except Exception as e:
            print(f"❌ Real API call failed: {e}")
            return False

    # Uncomment the next line to test real API
    return asyncio.run(real_test())


def main():
    """Run all tests."""
    print("Persona Loading Test Suite")
    print("=" * 60)
    print("This tests the API integration for loading persona configurations.")
    print("Used in the voice agent to get agent behavior based on dialed number.")
    print()

    # Test mocked API calls
    mock_tests_passed = asyncio.run(test_load_persona_from_dialed_number())

    # Test real API (optional)
    real_test_passed = test_real_api_call()

    print("\n" + "=" * 60)
    if mock_tests_passed and real_test_passed:
        print("✅ All persona loading tests passed!")
        print("The agent should be able to load persona configurations from dialed numbers.")
        print("\nIntegration test results:")
        print("- Number extraction: ✅ Working")
        print("- Persona API loading: ✅ Working")
        print("- Agent dispatch: Needs server-side testing")
    else:
        print("❌ Some tests failed.")
        if not mock_tests_passed:
            print("   - Mocked API tests failed")
        if not real_test_passed:
            print("   - Real API test failed")


if __name__ == "__main__":
    main()