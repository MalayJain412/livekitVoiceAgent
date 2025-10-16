# Dynamic Persona Loading (based on incoming caller number)

This document describes a complete, practical approach to dynamically loading a persona/prompt for the Friday AI voice agent based on the incoming caller number (Zoiper → SIP → livekit-sip → LiveKit → backend).

It contains architecture, recommended code changes, environment variables, testing steps, edge cases, and next steps for scaling.

---

## Goal

When a call arrives from a SIP client (Zoiper), extract the caller number and load a matching persona configuration. The persona will be used to update the agent's instructions (prompt) for that session so replies are tailored to the campaign/persona.

Currently available example mapping: `user-mapping/num_8655701159.json` and a public API:

`https://devcrm.xeny.ai/apis/api/public/mobile/<mobileNo>`

Important note: the JSON returned by this API uses the `mobileNo` field to indicate the phone number that the voicebot is mapped to (for example, `"mobileNo": "8655701159"`). When a call is received from that number, the backend should treat the API response as authoritative for the persona and full prompt configuration.

In other words: when a call is received from the caller number `8655701159`, the agent must call `https://devcrm.xeny.ai/apis/api/public/mobile/8655701159` and load the persona plus full prompt/instruction data from the API response. The API payload includes the `persona` object (voice agent config), `fullConfig`, `messages` (welcome/closing), and `personality` text which should be applied to the running session's instructions.

---

## High-level architecture

1. Zoiper sends SIP INVITE -> livekit-sip bridge parses SIP headers and injects caller data into `participant.metadata` or `room.metadata`.
2. LiveKit server bridges the SIP leg into a room and backend receives a participant-join / session start event.
3. Backend (`cagent.py`) reads caller metadata from room/participant metadata, or falls back to a default number for testing.
4. Backend calls persona API (`/apis/api/public/mobile/<caller>`) and extracts persona JSON (voice agent -> persona).
5. The backend attaches `caller_number` and `caller_persona` to the running `AgentSession`, and updates the agent instructions (best-effort) so the LLM prompt reflects the persona.
6. Transcript logger records the persona load event and the session proceeds.

---

## Files & code snippets

Note: these are minimal, non-invasive, best-effort suggestions. The repository already contains `cagent.py` and `transcript_logger.py` which are the right places to integrate.

### 1) Helper: load persona from API (sync helper used with asyncio.to_thread)

```python
import os
import logging
import requests

def load_persona_for_caller(caller, timeout=5):
    """Fetch persona JSON from public API for given caller number. Returns persona dict or None."""
    if not caller:
        return None
    try:
        base = os.getenv("PERSONA_API_BASE", "https://devcrm.xeny.ai/apis/api/public/mobile")
        url = f"{base}/{caller}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        campaigns = data.get("campaigns") or []
        if not campaigns:
            return None
        # pick first campaign -> first voiceAgent -> persona
        persona = campaigns[0]["voiceAgents"][0]["persona"]
        return persona
    except Exception as e:
        logging.warning(f"Failed to load persona for {caller}: {e}")
        return None
```

### 2) Detect caller and apply persona (non-blocking background task in `entrypoint`)

```python
# inside entrypoint after session.start(...)

async def _detect_and_apply_persona():
    caller = None
    try:
        room = getattr(session, "room", None)
        if room:
            # try room-level metadata
            room_meta = getattr(room, "metadata", None) or {}
            caller = room_meta.get("caller") or room_meta.get("caller_id") or room_meta.get("from")

            # try participant metadata
            if not caller:
                participants = getattr(room, "participants", None) or {}
                iterable = participants.values() if isinstance(participants, dict) else participants
                for p in iterable:
                    pmeta = getattr(p, "metadata", None) or {}
                    caller = pmeta.get("caller_id") or pmeta.get("callerNumber") or pmeta.get("from") or getattr(p, "identity", None)
                    if caller:
                        break
    except Exception:
        caller = None

    # fallback for testing
    if not caller:
        caller = os.getenv("DEFAULT_CALLER", "8655701159")

    setattr(session, "caller_number", caller)

    persona = await asyncio.to_thread(load_persona_for_caller, caller)
    if persona:
        setattr(session, "caller_persona", persona)
        # best-effort instruction update
        try:
            agent.instructions = persona.get("personality") or agent.instructions
        except Exception:
            pass

    # log a transcript event via transcript_logger.log_event

# start background task
asyncio.create_task(_detect_and_apply_persona())
```

### 3) Small prompts helper (optional)

Add in `prompts.py`:

```python
# existing AGENT_INSTRUCTION = "..."

def set_agent_instruction(text: str):
    """Set agent-level instructions at runtime (best-effort)."""
    global AGENT_INSTRUCTION
    AGENT_INSTRUCTION = text
```

Agent code can import and call `set_agent_instruction()` after loading persona.

---

## Environment variables

- PERSONA_API_BASE (optional) — default: https://devcrm.xeny.ai/apis/api/public/mobile
- DEFAULT_CALLER (optional) — default: 8655701159 (useful for local testing)
- MONGO_URI (optional) — if you migrate transcripts to MongoDB later

Set them in `.env` or your process env before starting the agent.

---

## Testing steps (manual)

1. Start livekit-sip and LiveKit server as you normally do.
2. Start the agent (the worker) locally with environment variables set. Example (PowerShell):

```powershell
$env:DEFAULT_CALLER = "8655701159"
python cagent.py
```

3. From Zoiper, call into the SIP bridge. Verify that `conversations/transcripts.jsonl` or `conversations/transcript_session_*.json` contains `persona_loaded` or `persona_not_found` events.
4. Verify that `session.caller_persona` exists if persona was found (you can add debug logs in `cagent.py` to print `session.caller_persona`).
5. To force a persona fetch for a given number, set `DEFAULT_CALLER` to that number before starting the agent.

---

## Edge cases & notes

- The persona API may be slow or occasionally fail — the implementation above runs persona fetching in a background thread and is best-effort. The session starts immediately; persona applies once available.
- If you want the persona to affect the very first reply, switch to a blocking fetch (await the persona before calling `session.generate_reply(...)`). This adds call setup latency (usually small, but depends on API speed).
- Different SIP bridges may use different metadata keys: `caller_id`, `callerNumber`, `from`, `sip_from`, or `identity`. The detection code checks common keys.
- Cache persona results in Redis or in-memory LRU if you expect many repeated calls for the same numbers.
- When moving to MongoDB, persist the full persona with the conversation for traceability and debugging.

---

## Next steps / follow-ups

- (Optional) Implement `set_agent_instruction()` in `prompts.py` and export a tiny helper to allow safe runtime updates.
- (Optional) Add a small patch to `tools.py` to let tools access `session.caller_persona` easily.
- (Optional) Add a small unit test that simulates a session with `DEFAULT_CALLER` and asserts `caller_persona` gets attached.
- (Optional) Add Redis caching for persona API responses.

---

## Example: blocking behaviour (if you want persona before first reply)

If you prefer the agent to *wait* for persona before generating the first reply, replace the background detection with a direct fetch and then continue:

```python
persona = await asyncio.to_thread(load_persona_for_caller, caller)
if persona:
    setattr(session, "caller_persona", persona)
    agent.instructions = persona.get("personality") or agent.instructions
# then continue with session.generate_reply(...)
```

This guarantees the first LLM call uses the persona instructions.

---

## Summary

I added a full plan and code examples for dynamically loading persona based on incoming caller number. The recommended integration point is `cagent.py` after `session.start(...)` where you can attach the persona to `AgentSession` and update agent instructions.

If you'd like, I can now:

- Create the small `prompts.py` helper (`set_agent_instruction`) and the `cagent.py` patch to actually implement the background persona load (non-blocking), and run quick local lint/tests. (I will only implement on your approval.)

---

Document created: docs/dynamic_persona_loading.md
