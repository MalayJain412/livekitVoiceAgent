# Friday AI — Copilot / Agent Instructions

Purpose: short, targeted guidance so an AI coding agent can be productive in this repository immediately, do not make any changes in the files with extension ".go"/go files.

## Quick start (PowerShell)

```powershell
# install deps
pip install -r requirements.txt

# build vector DB (required for RAG)
python model/build_db.py

# start webhook handler service (required for dynamic persona loading)
python handler.py

# run voice agent (in separate terminal)
python cagent.py

# run RAG web API (optional)
python model/runapi.py

# SIP telephony setup (requires Redis running)
redis-cli ping  # verify Redis is running
livekit-server --config livekit.yaml  # start main server
cd sip-setup && ./livekit-sip --config config.yaml  # start SIP bridge

# run tests (project uses simple python test scripts and pytest)
python test_tvenv_plugins.py
pytest test_handler.py test_integration.py -v  # webhook and persona loading tests
```

## What to read first (fast path)
- `handler.py` — NEW: webhook service for dynamic persona loading based on dialed number (264 lines)
- `cagent.py` — entrypoint: sets up JSONL logging, AgentSession, and reads persona from job metadata
- `transcript_logger.py` — background JSONL writer for realtime conversation logging
- `tools.py` — core function tools (triotech_info, create_lead, detect_lead_intent). Primary place for business logic
- `prompts.py` — agent/system prompts (Hinglish + lead capture rules)
- `config.py` — minimal helpers for conversations directory setup
- `model/build_db.py` and `model/runapi.py` — RAG build & runtime (Chroma DB, embeddings, API key rotation)
- `backup_plugin_modifications/` — modified LiveKit plugin stubs (`google_llm_modified.py`, `cartesia_tts_modified.py`) and `docker_scripts/` for applying them
- `sip-setup/config.yaml` and `livekit.yaml` — SIP bridge and server config (must have identical API keys)
- `Comprehensive Setup Guide_ Integrating a SIP Client with a Self-Hosted LiveKit Environment.md` — complete SIP setup walkthrough

## Key repository conventions (must follow exactly)
- User-facing language: Hinglish (brief Hindi+English). Lead confirmations/prompts are in Hinglish. See `prompts.py` for exact wording
- Lead storage: Lead JSON fields MUST be English (`name`, `email`, `company`, `interest`, `phone`, `budget`) — used for CRM downstream
- Tools: all user-facing tools follow the decorator pattern: `@function_tool()`
- Conversation logging: streaming JSONL at `conversations/transcripts.jsonl` + session snapshots at `conversations/transcript_session_<timestamp>.json`
- RAG chunk settings: chunk_size=1500, overlap=200 (see `model/build_db.py`)
- Environment config: Use `LLM_MODEL` env var to switch between Gemini models without code changes
- Dynamic persona loading: Webhook-based architecture where `handler.py` fetches persona configs before agent dispatch (NO agent-side API calls)
- Testing approach: Comprehensive pytest suite for webhook handler + integration tests for end-to-end persona loading flow

## Architecture & data flows
- Hybrid system: Fast JSON lookup in `data/` for basic queries → RAG fallback via `model/runapi.py` for deep queries (keywords: features/how to/api/integrate)
- Voice flow: STT → Agent (tools + RAG) → TTS. Realtime logging via `transcript_logger.py` (JSONL stream + session snapshots)
- Lead flow: `detect_lead_intent()` → `create_lead()` (validate → sanitize → write `leads/lead_YYYYMMDD_HHMMSS.json`)
- Integration: LiveKit server for real-time comms, Redis for SIP PSRPC, ChromaDB for vectors
- SIP telephony: Zoiper/softphone → livekit-sip (port 5060) → LiveKit server (port 7880) → voice agent. All services must connect to same Redis instance
- Logging architecture: Agent-level hooks capture STT chunks and session items → background worker writes to `conversations/transcripts.jsonl` → shutdown callback saves final snapshot
- **Dynamic persona loading flow**: SIP call → LiveKit participant_joined event → webhook handler fetches persona from API → handler dispatches agent with persona in job metadata → agent reads metadata and applies persona instructions

## Patterns & integration points
- Agent instrumentation: `cagent.py` uses `transcription_node()` for STT capture and background watcher for session history logging
- Plugin references: `backup_plugin_modifications/` holds patched stubs; `docker_scripts/apply_modifications.py` and `verify_modifications.py` apply/verify patches
- LiveKit: Token handling via `generate_livekit_token.py` for backend service integration
- RAG runtime: `model/runapi.py` handles embeddings, key rotation, queries to `model/chroma_db/`
- SIP setup: Create trunks via `lk sip inbound create` + dispatch rules via `lk sip dispatch create`. JSON configs in `sip-setup/inbound_trunk.json` and `sip-setup/sip_dispatch.json`
- **Webhook handler**: Flask service at `handler.py` responds to LiveKit events, fetches persona configs from https://devcrm.xeny.ai/apis/api/public/mobile/<mobileNo>, and dispatches agents with config metadata

## Debugging & tests
- Tests are small Python scripts (not pytest) — run directly for basic functionality
- Webhook testing: Use `pytest test_handler.py test_integration.py -v` for comprehensive persona loading flow testing
- Conversation logging: Check `conversations/transcripts.jsonl` for realtime events and `conversations/transcript_session_<timestamp>.json` for session snapshots
- After editing knowledge files, run `python model/build_db.py` to rebuild embeddings
- SIP debugging: Use `sngrep` for SIP traffic inspection, check Redis connection with `redis-cli ping`, verify room participants with `lk room participants --room friday-assistant-room`
- Webhook debugging: Test handler endpoints directly with curl or check Flask logs for persona API responses



## When changing behavior
- Add unit tests that exercise the `@function_tool()` functions and the lead creation/validation paths
- If you change RAG knowledge, rebuild DB and add a small integration test hitting `model/runapi.py`
- For webhook/persona loading changes, add tests to `test_handler.py` for API interactions and `test_integration.py` for end-to-end flows
- Test persona loading by dialing different numbers and verifying agent behavior matches expected persona configuration

## Repository cleanup & maintenance notes
- Keep `LIVEKIT_API_SECRET` only where tokens are minted; prefer backend as canonical token authority
- Leads and conversations contain PII — protect filesystem or move to secure DB; prefer atomic writes or file locks for concurrent processes
- SIP security: API keys in `livekit.yaml` and `sip-setup/config.yaml` must be identical. RTP ports 10000-20000 need firewall access
- Webhook service: `handler.py` must be running before SIP calls to ensure persona loading. Monitor Flask logs for API failures
- Test files `test_handler.py` and `test_integration.py` are NOT in repository yet but referenced in existing tests

## Files to inspect when working end-to-end
- Backend: `cagent.py`, `generate_livekit_token.py`, `tools.py`, `model/runapi.py`, `backup_plugin_modifications/`
- Webhook System: `handler.py` for persona loading service, missing `test_handler.py` and `test_integration.py` for testing
- SIP Setup: `sip-setup/config.yaml`, `livekit.yaml`, trunk/dispatch JSON configs
- Knowledge Base: `data/triotech_content.json`, `data/triotech_knowledge.txt`

When in doubt: prefer the backend as the canonical token service and add a read-only backend endpoint to surface leads if the frontend needs them.
