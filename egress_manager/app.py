import os
import time
import hmac
import hashlib
import json
from typing import Dict, Any
from datetime import datetime

import jwt
import requests
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
if LIVEKIT_API_SECRET:
    LIVEKIT_API_SECRET = LIVEKIT_API_SECRET.encode()
EGRESS_URL = os.getenv("EGRESS_URL", "http://localhost:7880/twirp/livekit.Egress")
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGODB_DB", "friday_ai")
RECORDINGS_PATH = os.getenv("RECORDINGS_PATH", "/recordings")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

app = FastAPI(title="LiveKit Egress Manager")

# Mongo
client = None
recordings_col = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB]
        recordings_col = db["recordings"]
    except Exception:
        client = None
        recordings_col = None


def generate_recorder_token(room_name: str, ttl_seconds: int = 3600) -> str:
    """Create a LiveKit access token (JWT) with roomRecord permission for the recorder."""
    now = int(time.time())
    payload = {
        "jti": f"recorder-{room_name}-{now}",
        "iss": LIVEKIT_API_KEY,
        "sub": "egress-recorder",
        "nbf": now - 10,
        "iat": now,
        "exp": now + ttl_seconds,
        "grants": {
            "room": room_name,
            "roomRecord": True,
        },
    }
    if not LIVEKIT_API_SECRET:
        raise RuntimeError("LIVEKIT_API_SECRET not configured")
    token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode()
    return token


def start_participant_egress(room_name: str, identity: str) -> Dict[str, Any]:
    token = generate_recorder_token(room_name)
    url = f"{EGRESS_URL}/StartParticipantEgress"
    filepath = f"{RECORDINGS_PATH}/{room_name}-{identity}-{{time}}.mp4"
    payload = {
        "room_name": room_name,
        "identity": identity,
        "audio_only": True,
        "file_outputs": [
            {
                "filepath": filepath,
                "disable_video": True,
            }
        ],
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    return res.json()


def start_track_egress(room_name: str, track_id: str) -> Dict[str, Any]:
    token = generate_recorder_token(room_name)
    url = f"{EGRESS_URL}/StartTrackEgress"
    filepath = f"{RECORDINGS_PATH}/{room_name}-{track_id}-{{time}}.ogg"
    payload = {
        "room_name": room_name,
        "track_id": track_id,
        "file": {"filepath": filepath},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    return res.json()


def stop_egress(egress_id: str) -> Dict[str, Any]:
    token = generate_recorder_token("")
    url = f"{EGRESS_URL}/StopEgress"
    payload = {"egress_id": egress_id}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    return res.json()


class WebhookEvent(BaseModel):
    type: str
    info: dict = {}


def verify_signature(raw: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        return True
    mac = hmac.new(WEBHOOK_SECRET.encode(), raw, digestmod=hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.post("/webhook")
async def webhook(request: Request, x_signature: str = Header(None)):
    body = await request.body()
    if not verify_signature(body, x_signature or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")
    payload = await request.json()
    event_type = payload.get("event") or payload.get("type")
    # participant joined
    if event_type == "participant_joined":
        room = payload.get("room", {})
        room_name = room.get("name") or room.get("sid")
        participant = payload.get("participant") or {}
        identity = participant.get("identity") or participant.get("sid") or "unknown"
        phone = participant.get("metadata", {}).get("phone") or participant.get("name")
        try:
            info = start_participant_egress(room_name, identity)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
        doc = {
            "room_name": room_name,
            "egress_id": info.get("egress_id"),
            "caller_number": phone,
            "agent_identity": identity,
            "filepath": None,
            "started_at": datetime.utcnow(),
            "stopped_at": None,
            "duration_sec": None,
            "status": "starting",
            "tracks": []  # Array to hold individual track recordings
        }
        if recordings_col is not None:
            recordings_col.insert_one(doc)
        return {"status": "ok", "started": info}
    
    # track published - start individual track recording
    if event_type == "track_published":
        room = payload.get("room", {})
        room_name = room.get("name") or room.get("sid")
        participant = payload.get("participant", {})
        identity = participant.get("identity") or participant.get("sid") or "unknown"
        track = payload.get("track", {})
        track_id = track.get("sid")
        track_type = track.get("type")
        participant_kind = participant.get("kind")
        
        # Only start TrackEgress for audio tracks from SIP participants
        if track_type == "AUDIO" and participant_kind == "SIP":
            try:
                info = start_track_egress(room_name, track_id)
                track_egress_id = info.get("egress_id")
                
                # Find the main recording document and add this track's info
                # This links the raw track file to the main call record
                if recordings_col is not None:
                    recordings_col.update_one(
                        {"room_name": room_name, "agent_identity": identity, "status": "starting"},
                        {"$push": {"tracks": {
                            "track_id": track_id,
                            "egress_id": track_egress_id,
                            "filepath": None,
                            "status": "starting"
                        }}}
                    )
                return {"status": "ok", "started_track_egress": info}
            except Exception as e:
                print(f"Error starting Track Egress for track {track_id}: {e}")
                # Return 200 OK to prevent LiveKit from retrying the webhook
                return {"status": "error", "message": str(e)}
    
    if event_type == "egress_completed":
        info = payload.get("info", {})
        egress_id = info.get("egress_id") or payload.get("egress_id")
        out = info.get("outputs") or info.get("file_outputs") or {}
        filepath = None
        try:
            if "file" in info:
                filepath = info["file"].get("filepath")
            elif isinstance(out, list) and len(out) > 0:
                filepath = out[0].get("filepath")
        except Exception:
            filepath = None
        
        stopped_at = datetime.utcnow()
        
        if recordings_col is not None:
            # First try to update as a main recording (ParticipantEgress)
            updated = recordings_col.update_one(
                {"egress_id": egress_id},
                {"$set": {"status": "completed", "stopped_at": stopped_at, "filepath": filepath}}
            )
            
            # If not found as a main egress, it must be a track egress (TrackEgress)
            if updated.matched_count == 0:
                recordings_col.update_one(
                    {"tracks.egress_id": egress_id},
                    {"$set": {
                        "tracks.$.status": "completed",
                        "tracks.$.filepath": filepath
                    }}
                )
        
        return {"status": "ok"}
    return {"status": "ignored", "event": event_type}
