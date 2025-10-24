#!/usr/bin/env python3
"""
Test script for the enhanced Egress Manager with dual recording capability.
Tests both ParticipantEgress (mixed MP4) and TrackEgress (individual OGG) flows.
"""

import json
import time
import requests
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
EGRESS_MANAGER_URL = "http://localhost:5000"
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGODB_DB", "friday_ai")

def test_participant_joined_webhook():
    """Test that participant_joined starts ParticipantEgress and creates MongoDB doc."""
    print("\n=== Testing participant_joined webhook ===")
    
    payload = {
        "event": "participant_joined",
        "room": {
            "name": "test-room-" + str(int(time.time())),
            "sid": "RM_test123"
        },
        "participant": {
            "identity": "sip_test_1001",
            "sid": "PA_test456",
            "name": "+911234567890",
            "metadata": {"phone": "+911234567890"}
        }
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{EGRESS_MANAGER_URL}/webhook",
            json=payload,
            timeout=10
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ participant_joined webhook handled successfully")
            return payload["room"]["name"], payload["participant"]["identity"]
        else:
            print("❌ participant_joined webhook failed")
            return None, None
            
    except Exception as e:
        print(f"❌ Error testing participant_joined: {e}")
        return None, None

def test_track_published_webhook(room_name, identity):
    """Test that track_published starts TrackEgress and updates MongoDB tracks array."""
    print("\n=== Testing track_published webhook ===")
    
    payload = {
        "event": "track_published",
        "room": {
            "name": room_name,
            "sid": "RM_test123"
        },
        "participant": {
            "identity": identity,
            "sid": "PA_test456",
            "kind": "SIP"
        },
        "track": {
            "sid": "TR_audio_test789",
            "type": "AUDIO"
        }
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{EGRESS_MANAGER_URL}/webhook",
            json=payload,
            timeout=10
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ track_published webhook handled successfully")
        else:
            print("❌ track_published webhook failed")
            
    except Exception as e:
        print(f"❌ Error testing track_published: {e}")

def test_egress_completed_webhook(room_name, egress_id, is_track=False):
    """Test that egress_completed updates the correct MongoDB document."""
    print(f"\n=== Testing egress_completed webhook ({'track' if is_track else 'participant'}) ===")
    
    filepath = f"/recordings/{room_name}-{'TR_audio_test789' if is_track else 'sip_test_1001'}-2025-10-24T10-30-00.{'ogg' if is_track else 'mp4'}"
    
    payload = {
        "event": "egress_completed",
        "info": {
            "egress_id": egress_id,
            "room_name": room_name,
            "outputs": [
                {"filepath": filepath}
            ],
            "duration_seconds": 32
        }
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{EGRESS_MANAGER_URL}/webhook",
            json=payload,
            timeout=10
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ egress_completed webhook handled successfully")
        else:
            print("❌ egress_completed webhook failed")
            
    except Exception as e:
        print(f"❌ Error testing egress_completed: {e}")

def verify_mongodb_state(room_name):
    """Verify that MongoDB documents are created and updated correctly."""
    print("\n=== Verifying MongoDB state ===")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB]
        recordings_col = db["recordings"]
        
        # Find the recording document
        doc = recordings_col.find_one({"room_name": room_name})
        
        if doc:
            print("✅ Found recording document in MongoDB:")
            print(f"   Room: {doc.get('room_name')}")
            print(f"   Status: {doc.get('status')}")
            print(f"   Egress ID: {doc.get('egress_id')}")
            print(f"   Filepath: {doc.get('filepath')}")
            print(f"   Tracks: {len(doc.get('tracks', []))} track(s)")
            
            for i, track in enumerate(doc.get('tracks', [])):
                print(f"     Track {i+1}: {track.get('track_id')} - {track.get('status')}")
                
            return True
        else:
            print("❌ No recording document found in MongoDB")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying MongoDB: {e}")
        return False

def test_health_endpoint():
    """Test that the Egress Manager is running."""
    print("=== Testing Egress Manager health ===")
    
    try:
        response = requests.get(f"{EGRESS_MANAGER_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Egress Manager is running (FastAPI docs accessible)")
            return True
        else:
            print("❌ Egress Manager may not be running properly")
            return False
    except Exception as e:
        print(f"❌ Cannot reach Egress Manager: {e}")
        print("   Make sure to start it with: uvicorn egress_manager.app:app --host 0.0.0.0 --port 5000")
        return False

def main():
    """Run comprehensive test suite for enhanced recording system."""
    print("🎯 Enhanced Recording System Test Suite")
    print("="*50)
    
    # Check if Egress Manager is running
    if not test_health_endpoint():
        print("\n❌ Test suite aborted - Egress Manager not accessible")
        return
    
    # Test the full flow
    room_name, identity = test_participant_joined_webhook()
    
    if room_name and identity:
        # Give a moment for the ParticipantEgress to be processed
        time.sleep(2)
        
        # Test track publishing
        test_track_published_webhook(room_name, identity)
        
        # Give a moment for the TrackEgress to be processed
        time.sleep(2)
        
        # Simulate completion events (you would normally get real egress_ids from the responses)
        test_egress_completed_webhook(room_name, "EG_participant_test123", is_track=False)
        test_egress_completed_webhook(room_name, "EG_track_test456", is_track=True)
        
        # Verify final MongoDB state
        time.sleep(1)
        verify_mongodb_state(room_name)
    
    print("\n🏁 Test suite completed!")
    print("\nWhat to check next:")
    print("1. Verify /recordings folder contains the expected .mp4 and .ogg files")
    print("2. Check MongoDB 'recordings' collection for complete metadata")
    print("3. Make a real SIP call to test end-to-end flow")

if __name__ == "__main__":
    main()