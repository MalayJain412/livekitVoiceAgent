#!/usr/bin/env python3
"""
Test script for validation logic to debug why calls are being rejected.
"""

import sys
import os
import json
from datetime import datetime
import pytz

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validation import validate_agent_availability

# The API response from the user's test
test_config = {
    "mobileNo": "+918655054859",
    "campaigns": [
        {
            "campaignId": "68fdfa6183fc73d5cd04af79",
            "campaignName": "Ahmedtest",
            "campaignType": "inbound",
            "status": "active",
            "numbers": {
                "singleNumber": "+918655054859",
                "concurrency": 1,
                "numberArray": [],
                "numberSource": "single"
            },
            "schedule": {
                "startDate": "2025-10-26T00:00:00.000Z",
                "endDate": "2025-11-01T00:00:00.000Z",
                "timeZone": "IST",
                "activeHours": {
                    "start": "09:00",
                    "end": "23:00"
                },
                "daysOfWeek": [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday"
                ]
            },
            "client": {
                "id": "68c902bf1d21e95f946250f3",
                "name": "Xeny Demo",
                "companyName": "XenyDemo",
                "email": "xeny@xeny.ai",
                "credits": {
                    "balance": 61.17333333333337,
                    "totalEarned": 1010,
                    "totalSpent": 940.18
                }
            },
            "voiceAgents": [
                {
                    "id": "68fd1c1d83fc73d5cd045c73",
                    "name": "Test bot",
                    "type": "support",
                    "status": "busy",
                    "voiceDetails": {
                        "id": "68fe5cbb33cf583ed3059e2b",
                        "name": "adam",
                        "gender": "male",
                        "language": "ENGLISH",
                        "accent": "American",
                        "age": "adult",
                        "voiceModel": "ElevenLabs",
                        "quality": "premium_realistic"
                    },
                    "persona": {
                        "id": "68fd1c1d83fc73d5cd045c73",
                        "name": "Test bot",
                        "language": "English",
                        "additionalLanguages": [
                            "Urdu",
                            "Hindi"
                        ],
                        "voice": "adam",
                        "welcomeMessage": "Hello I am Imran",
                        "closingMessage": "Bye",
                        "transferNumber": "",
                        "personality": "You are Imran, A voice agent which help people",
                        "conversationStructure": "-",
                        "workflow": "-",
                        "knowledgeBase": "-",
                        "dataFields": [
                            {
                                "field": "",
                                "type": "Text",
                                "description": "",
                                "_id": "68fd1c1d83fc73d5cd045c74",
                                "id": "68fd1c1d83fc73d5cd045c74"
                            }
                        ],
                        "status": "busy",
                        "client": "68c902bf1d21e95f946250f3",
                        "createdBy": "68c902bf1d21e95f946250f5",
                        "tags": [],
                        "version": "1.0.0",
                        "createdAt": "2025-10-25T18:51:09.651Z",
                        "updatedAt": "2025-10-26T17:43:29.712Z"
                    },
                    "createdAt": "2025-10-25T18:51:09.651Z",
                    "updatedAt": "2025-10-26T17:43:29.712Z"
                }
            ],
            "createdAt": "2025-10-26T10:39:29.676Z",
            "updatedAt": "2025-10-26T16:05:12.197Z"
        }
    ],
    "totalCampaigns": 1,
    "searchDigits": "55054859"
}

def main():
    print("Validation Debug Test")
    print("=" * 50)

    # Check current time info
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    print(f"Current time (IST): {now}")
    print(f"Current date: {now.date()}")
    print(f"Day of week: {now.strftime('%A').lower()}")
    print(f"Current time: {now.strftime('%H:%M')}")
    print()

    # Test validation
    is_available, failure_reason = validate_agent_availability(test_config)

    print("Validation Result:")
    print(f"Available: {is_available}")
    print(f"Failure Reason: '{failure_reason}'")
    print()

    if not is_available:
        print("❌ Validation failed - call will be rejected")
        print(f"Reason: {failure_reason}")

        # Analyze the schedule
        campaign = test_config["campaigns"][0]
        schedule = campaign["schedule"]
        client = campaign["client"]

        print("\nSchedule Analysis:")
        print(f"Date range: {schedule['startDate']} to {schedule['endDate']}")
        print(f"Timezone: {schedule['timeZone']}")
        print(f"Active hours: {schedule['activeHours']['start']} - {schedule['activeHours']['end']}")
        print(f"Allowed days: {schedule['daysOfWeek']}")
        print(f"Current day: {now.strftime('%A').lower()}")

        print(f"\nCredit balance: {client['credits']['balance']}")
        print(f"Campaign status: {campaign['status']}")

    else:
        print("✅ Validation passed - call should proceed")

if __name__ == "__main__":
    main()