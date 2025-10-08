# Friday AI — Copilot / Agent Instructions

Purpose: short, targeted guidance so an AI coding agent can be productive in this repository immediately, do not make any changes in the files with extension ".go"/go files.

## Quick start (PowerShell)

```powershell
# install deps
pip install -r requirements.txt

# build vector DB (required for RAG)
python model/build_db.py

# run voice agent
python cagent.py

# run RAG web API
python model/runapi.py

# SIP telephony setup (requires Redis running)
redis-cli ping  # verify Redis is running
livekit-server --config livekit.yaml  # start main server
cd sip-setup && ./livekit-sip --config config.yaml  # start SIP bridge

# run tests (project uses simple python test scripts)
python test_triotech_assistant.py
python test_dummy_plugins.py
python test_lead_detection.py
```

## What to read first (fast path)
- `cagent.py` — entrypoint: sets up conversation logging and AgentSession.
- `tools.py` — core function tools (triotech_info, create_lead, detect_lead_intent). Primary place for business logic.
- `prompts.py` — agent/system prompts (Hinglish + lead capture rules).
- `config.py` — conversation log path helpers and helpers used across tests/plugins.
- `model/build_db.py` and `model/runapi.py` — RAG build & runtime (Chroma DB, embeddings, API key rotation).
- `backup_plugin_modifications/` — modified LiveKit plugin stubs (`google_llm_modified.py`, `cartesia_tts_modified.py`) and `docker_scripts/` for applying them.
- `sip/config.yaml` and `livekit.yaml` — SIP bridge and server config (must have identical API keys).
- `Comprehensive Setup Guide_ Integrating a SIP Client with a Self-Hosted LiveKit Environment.md` — complete SIP setup walkthrough.

## Key repository conventions (must follow exactly)
- User-facing language: Hinglish (brief Hindi+English). Lead confirmations/prompts are in Hinglish. See `prompts.py` for exact wording.
- Lead storage: Lead JSON fields MUST be English (`name`, `email`, `company`, `interest`, `phone`, `budget`) — used for CRM downstream.
- Tools: all user-facing tools follow the decorator pattern: `@function_tool()`.
- Conversation log name: `conversations/conversation_YYYYMMDD_HHMMSS.json` (use `config.setup_conversation_log()`).
- RAG chunk settings: chunk_size=1500, overlap=200 (see `model/build_db.py`).

## Architecture & data flows
- Hybrid system: Fast JSON lookup in `data/` for basic queries → RAG fallback via `model/runapi.py` for deep queries (keywords: features/how to/api/integrate).
- Voice flow: STT → Agent (tools + RAG) → TTS. SIP for phone calls (inbound/outbound).
- Lead flow: `detect_lead_intent()` → `create_lead()` (validate → sanitize → write `leads/lead_YYYYMMDD_HHMMSS.json`).
- Integration: LiveKit server for real-time comms, Redis for SIP PSRPC, ChromaDB for vectors.
- SIP telephony: Zoiper/softphone → livekit-sip (port 5060) → LiveKit server (port 7880) → voice agent. All services must connect to same Redis instance.

## Patterns & integration points
- Plugins: `backup_plugin_modifications/` holds patched stubs; `docker_scripts/apply_modifications.py` and `verify_modifications.py` apply/verify patches.
- LiveKit: Token handling critical (frontend: `friday-frontend/src/app/api/livekit/token/route.ts`).
- RAG runtime: `model/runapi.py` handles embeddings, key rotation, queries to `model/chroma_db/`.
- SIP setup: Create trunks via `lk sip inbound create` + dispatch rules via `lk sip dispatch create`. JSON configs in `sip/inbound_trunk.json` and `sip/sip_dispatch.json`.

## Debugging & tests
- Tests are small Python scripts (not pytest) — run directly.
- Inspect conversation log path: `python -c "import config; print(config.get_conversation_log_path())"`.
- After editing knowledge files, run `python model/build_db.py` to rebuild embeddings.
- SIP debugging: Use `sngrep` for SIP traffic inspection, check Redis connection with `redis-cli ping`, verify room participants with `lk room participants --room friday-assistant-room`.

## Security & operations notes
- Keep `LIVEKIT_API_SECRET` only where tokens are minted; prefer backend as canonical token authority.
- Leads and conversations contain PII — protect filesystem or move to secure DB; prefer atomic writes or file locks for concurrent processes.
- SIP security: API keys in `livekit.yaml` and `sip/config.yaml` must be identical. RTP ports 10000-20000 need firewall access.

## When changing behavior
- Add unit tests that exercise the `@function_tool()` functions and the lead creation/validation paths.
- If you change RAG knowledge, rebuild DB and add a small integration test hitting `model/runapi.py`.

## Files to inspect when working end-to-end
- Frontend: `friday-frontend/src/app/api/livekit/token/route.ts`, `friday-frontend/src/components/voice-assistant.tsx`
- Backend: `cagent.py`, `generate_livekit_token.py`, `tools.py`, `model/runapi.py`, `backup_plugin_modifications/`

When in doubt: prefer the backend as the canonical token service and add a read-only backend endpoint to surface leads if the frontend needs them.
