#!/usr/bin/env python3
"""
Test script for Asterisk dialed number extraction
Simulates webhook calls that would come from LiveKit when Asterisk makes calls
"""

import json
import requests
import time

def test_webhook_with_asterisk_data():
    """Test the webhook handler with simulated Asterisk call data"""
    
    # Test webhook URL (adjust port if different)
    webhook_url = "http://localhost:8080/livekit-webhook"
    
    # Simulate different scenarios of how Asterisk might send dialed number info
    test_scenarios = [
        {
            "name": "Scenario 1: SIP To Header",
            "payload": {
                "event": "participant_joined",
                "room": {
                    "name": "friday-assistant-room",
                    "sid": "RM_test123"
                },
                "participant": {
                    "kind": "sip",
                    "identity": "sip_caller123",
                    "attributes": {
                        "sip.toUser": "918655054859",  # Dialed number in To header
                        "sip.fromUser": "+916232155888",  # Caller number
                        "sip.callStatus": "active"
                    },
                    "metadata": {}
                }
            }
        },
        {
            "name": "Scenario 2: SIP Request URI",
            "payload": {
                "event": "participant_joined",
                "room": {
                    "name": "friday-assistant-room",
                    "sid": "RM_test124"
                },
                "participant": {
                    "kind": "sip",
                    "identity": "sip_caller124",
                    "attributes": {
                        "sip.requestURI": "sip:918655054859@20.193.141.77",  # Full SIP URI
                        "sip.fromUser": "+916232155888",
                        "sip.callStatus": "active"
                    },
                    "metadata": {}
                }
            }
        },
        {
            "name": "Scenario 3: Custom X-Dialed-Number Header",
            "payload": {
                "event": "participant_joined",
                "room": {
                    "name": "friday-assistant-room",
                    "sid": "RM_test125"
                },
                "participant": {
                    "kind": "sip",
                    "identity": "sip_caller125",
                    "attributes": {
                        "sip.X-Dialed-Number": "918655054859",  # Custom header
                        "sip.fromUser": "+916232155888",
                        "sip.callStatus": "active"
                    },
                    "metadata": {}
                }
            }
        },
        {
            "name": "Scenario 4: Room-based routing",
            "payload": {
                "event": "participant_joined",
                "room": {
                    "name": "room-918655054859",  # Room name contains dialed number
                    "sid": "RM_test126"
                },
                "participant": {
                    "kind": "sip",
                    "identity": "sip_caller126",
                    "attributes": {
                        "sip.fromUser": "+916232155888",
                        "sip.callStatus": "active"
                    },
                    "metadata": {}
                }
            }
        },
        {
            "name": "Scenario 5: No dialed number (debug test)",
            "payload": {
                "event": "participant_joined",
                "room": {
                    "name": "friday-assistant-room",
                    "sid": "RM_test127"
                },
                "participant": {
                    "kind": "sip",
                    "identity": "sip_caller127",
                    "attributes": {
                        "sip.fromUser": "+916232155888",  # Only caller number
                        "sip.callStatus": "active"
                    },
                    "metadata": {}
                }
            }
        }
    ]
    
    print("🧪 Testing Asterisk Dialed Number Extraction")
    print("=" * 50)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 30)
        
        try:
            response = requests.post(
                webhook_url,
                json=scenario['payload'],
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("✅ Webhook processed successfully")
            else:
                print(f"❌ Webhook failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed - Make sure webhook handler is running")
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Small delay between tests

if __name__ == "__main__":
    print("Make sure to start the webhook handler first:")
    print("python handler.py")
    print()
    input("Press Enter when webhook handler is running...")
    
    test_webhook_with_asterisk_data()