#!/usr/bin/env python3
"""Generate a LiveKit access token (JWT) for development.

Usage:
  python generate_livekit_token.py            # prints a token using env or .env values
  python generate_livekit_token.py --identity alice --room myroom

This script reads LIVEKIT_API_KEY and LIVEKIT_API_SECRET from the environment
or from a .env file if present (uses python-dotenv).

Security: never expose LIVEKIT_API_SECRET in browser code or commit it to a repo.
For production, sign tokens server-side and provide them to clients via a protected
server endpoint.
"""
from __future__ import annotations

import time
import uuid
import json
import argparse
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; environment variables will still work
    pass

try:
    import jwt  # PyJWT
except Exception as e:
    raise SystemExit(
        "PyJWT is required. Install with: pip install PyJWT python-dotenv"
    ) from e


def generate_token(api_key: str, api_secret: str, identity: str, room: Optional[str], ttl: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "jti": str(uuid.uuid4()),
        "iss": api_key,
        "sub": identity,
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        "grants": {},
    }

    # Attach video grant
    video_grant = {"room_join": True}
    if room:
        video_grant["room"] = room

    payload["grants"]["video"] = video_grant

    headers = {"kid": api_key}

    token = jwt.encode(payload, api_secret, algorithm="HS256", headers=headers)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def main() -> None:
    p = argparse.ArgumentParser(description="Generate LiveKit access token (JWT)")
    p.add_argument("--identity", default=os.environ.get("IDENTITY", "user123"), help="identity/subject to put in token")
    p.add_argument("--room", default=os.environ.get("ROOM", "test-room"), help="room name (optional)")
    p.add_argument("--any-room", action="store_true", help="omit room restriction so token can join any room (server policy permitting)")
    p.add_argument("--ttl", type=int, default=int(os.environ.get("TTL", "3600")), help="time-to-live in seconds")
    p.add_argument("--key", default=os.environ.get("LIVEKIT_API_KEY"), help="LiveKit API key (overrides env)")
    p.add_argument("--secret", default=os.environ.get("LIVEKIT_API_SECRET"), help="LiveKit API secret (overrides env)")
    p.add_argument("--inspect", action="store_true", help="print token header and payload (no signature verify)")

    args = p.parse_args()

    api_key = args.key
    api_secret = args.secret

    if not api_key or not api_secret:
        print("Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in environment or passed with --key/--secret")
        raise SystemExit(2)

    # if --any-room passed, treat room as None so generator omits the room field
    room_arg = None if args.any_room else (args.room or None)
    token = generate_token(api_key, api_secret, args.identity, room_arg, ttl=args.ttl)
    print(token)

    if args.inspect:
        # Show header and payload without verifying signature
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        print("\n-- header --")
        print(json.dumps(header, indent=2))
        print("\n-- payload --")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
