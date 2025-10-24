#!/usr/bin/env python3
"""
Unit tests for the enhanced Egress Manager webhook logic.
Tests the webhook handlers without requiring actual LiveKit services.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the parent directory to sys.path to import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, recordings_col
from fastapi.testclient import TestClient

client = TestClient(app)

class TestEnhancedRecording:
    """Test suite for the enhanced dual recording system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_room = "test-room-12345"
        self.test_identity = "sip_test_1001"
        self.test_track_id = "TR_audio_test789"
        self.test_phone = "+911234567890"

    @patch('app.start_participant_egress')
    @patch('app.recordings_col')
    def test_participant_joined_creates_recording(self, mock_recordings_col, mock_start_egress):
        """Test that participant_joined creates a ParticipantEgress and MongoDB doc."""
        # Mock the egress start response
        mock_start_egress.return_value = {"egress_id": "EG_participant_123"}
        
        # Mock MongoDB collection
        mock_recordings_col.insert_one = Mock()
        
        payload = {
            "event": "participant_joined",
            "room": {"name": self.test_room, "sid": "RM_test123"},
            "participant": {
                "identity": self.test_identity,
                "sid": "PA_test456",
                "name": self.test_phone,
                "metadata": {"phone": self.test_phone}
            }
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "started" in response.json()
        
        # Verify egress was started
        mock_start_egress.assert_called_once_with(self.test_room, self.test_identity)
        
        # Verify MongoDB document was created with tracks array
        mock_recordings_col.insert_one.assert_called_once()
        doc = mock_recordings_col.insert_one.call_args[0][0]
        
        assert doc["room_name"] == self.test_room
        assert doc["agent_identity"] == self.test_identity
        assert doc["caller_number"] == self.test_phone
        assert doc["egress_id"] == "EG_participant_123"
        assert doc["status"] == "starting"
        assert "tracks" in doc
        assert doc["tracks"] == []

    @patch('app.start_track_egress')
    @patch('app.recordings_col')
    def test_track_published_starts_track_egress(self, mock_recordings_col, mock_start_track_egress):
        """Test that track_published starts TrackEgress for SIP audio tracks."""
        # Mock the track egress start response
        mock_start_track_egress.return_value = {"egress_id": "EG_track_456"}
        
        # Mock MongoDB collection update
        mock_recordings_col.update_one = Mock()
        
        payload = {
            "event": "track_published",
            "room": {"name": self.test_room, "sid": "RM_test123"},
            "participant": {
                "identity": self.test_identity,
                "sid": "PA_test456",
                "kind": "SIP"
            },
            "track": {
                "sid": self.test_track_id,
                "type": "AUDIO"
            }
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "started_track_egress" in response.json()
        
        # Verify track egress was started
        mock_start_track_egress.assert_called_once_with(self.test_room, self.test_track_id)
        
        # Verify MongoDB tracks array was updated
        mock_recordings_col.update_one.assert_called_once()
        filter_query, update_query = mock_recordings_col.update_one.call_args[0]
        
        assert filter_query["room_name"] == self.test_room
        assert filter_query["agent_identity"] == self.test_identity
        assert filter_query["status"] == "starting"
        
        track_info = update_query["$push"]["tracks"]
        assert track_info["track_id"] == self.test_track_id
        assert track_info["egress_id"] == "EG_track_456"
        assert track_info["status"] == "starting"

    @patch('app.recordings_col')
    def test_track_published_ignores_non_sip_tracks(self, mock_recordings_col):
        """Test that non-SIP tracks are ignored."""
        payload = {
            "event": "track_published",
            "room": {"name": self.test_room},
            "participant": {
                "identity": "agent_user",
                "kind": "STANDARD"  # Not SIP
            },
            "track": {
                "sid": self.test_track_id,
                "type": "AUDIO"
            }
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        
        # Verify no MongoDB operations
        mock_recordings_col.update_one.assert_not_called()

    @patch('app.recordings_col')
    def test_egress_completed_updates_main_recording(self, mock_recordings_col):
        """Test that egress_completed updates main recording correctly."""
        # Mock successful update (matched_count > 0)
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_recordings_col.update_one.return_value = mock_result
        
        payload = {
            "event": "egress_completed",
            "info": {
                "egress_id": "EG_participant_123",
                "room_name": self.test_room,
                "outputs": [
                    {"filepath": f"/recordings/{self.test_room}-{self.test_identity}-2025-10-24T10-30-00.mp4"}
                ],
                "duration_seconds": 32
            }
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # Verify main recording was updated
        mock_recordings_col.update_one.assert_called_once()
        filter_query, update_query = mock_recordings_col.update_one.call_args[0]
        
        assert filter_query["egress_id"] == "EG_participant_123"
        assert update_query["$set"]["status"] == "completed"
        assert update_query["$set"]["filepath"].endswith(".mp4")

    @patch('app.recordings_col')
    def test_egress_completed_updates_track_recording(self, mock_recordings_col):
        """Test that egress_completed updates track recording when main not found."""
        # Mock failed first update (matched_count = 0), then successful second update
        mock_result = Mock()
        mock_result.matched_count = 0
        mock_recordings_col.update_one.return_value = mock_result
        
        payload = {
            "event": "egress_completed",
            "info": {
                "egress_id": "EG_track_456",
                "room_name": self.test_room,
                "outputs": [
                    {"filepath": f"/recordings/{self.test_room}-{self.test_track_id}-2025-10-24T10-30-00.ogg"}
                ]
            }
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # Verify both update attempts were made
        assert mock_recordings_col.update_one.call_count == 2
        
        # Check first call (main recording attempt)
        first_call = mock_recordings_col.update_one.call_args_list[0]
        assert first_call[0][0]["egress_id"] == "EG_track_456"
        
        # Check second call (track recording update)
        second_call = mock_recordings_col.update_one.call_args_list[1]
        assert second_call[0][0]["tracks.egress_id"] == "EG_track_456"
        assert second_call[0][1]["$set"]["tracks.$.status"] == "completed"
        assert second_call[0][1]["$set"]["tracks.$.filepath"].endswith(".ogg")

    def test_unknown_event_ignored(self):
        """Test that unknown events are gracefully ignored."""
        payload = {
            "event": "unknown_event_type",
            "data": {"some": "data"}
        }
        
        response = client.post("/webhook", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert response.json()["event"] == "unknown_event_type"

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])