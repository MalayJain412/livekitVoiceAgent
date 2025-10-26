## Friday AI — Copilot / Agent Instructions (concise)

Purpose: short, targeted guidance so an AI coding agent can be productive immediately in this repo.

Quick actions (Windows PowerShell)
- Install deps: `pip install -r requirements.txt`
- Build RAG DB: `python model/build_db.py`
- Start voice agent: `python cagent.py` (direct number extraction, no webhook needed)
- Run RAG API (optional): `python model/runapi.py`

Where to read first (high signal files)
- `cagent.py` — main entrypoint with direct number extraction and persona loading
- `persona_handler.py` — API-based persona loader with room inspection
- `tools.py` — business logic functions (decorated with `@function_tool()`)
- `prompts.py` — user-facing Hinglish prompts and lead-capture rules
- `transcript_logger.py` — realtime JSONL logging and final snapshot logic

Project conventions (explicit, non-negotiable)
- User-facing language: Hinglish (see `prompts.py` for exact phrases).
- Lead files: JSON fields MUST be English: `name,email,company,interest,phone,budget` (used downstream).
- Tools: use the `@function_tool()` decorator for user-facing tool functions (see `tools.py`).
- Persona loading: Always from CRM API based on extracted dialed number.
- Voice mapping: `voices/all_voices.json` and `instances.py` contain TTS/STT provider wiring.

Important flows & integration points (short)
- Voice flow: STT -> Agent (tools + RAG) -> TTS. Key files: `instances.py`, `tools.py`, `prompts.py`.
- Persona flow: SIP call -> LiveKit room -> `cagent.py` extracts number -> API call -> persona config applied.
- Lead flow: `detect_lead_intent()` -> `create_lead()` (sanitizes & writes to `leads/`).
- RAG: `model/build_db.py` (chunk_size=1500, overlap=200) and `model/runapi.py` handle embeddings & queries.

Testing & debug notes (practical)
- Small scripts exist for component checks (see `tests/`); run unit-like scripts directly with Python.
- Integration tests use pytest: e.g. `pytest tests/test_handler.py tests/test_integration.py -v`.
- Conversation logs: `conversations/transcripts.jsonl` (stream) and `conversations/transcript_session_<ts>.json` (snapshots).

Quick pointers for agents editing code
- When modifying persona or webhook behavior, update `tests/test_handler.py` and `tests/test_integration.py`.
- If you change RAG content/format, run `python model/build_db.py` and add a small integration test for `model/runapi.py`.
- Preserve Hinglish prompts in `prompts.py` exactly when altering user-facing flows.

Files to inspect for examples
- `handler.py`, `cagent.py`, `persona_handler.py`, `tools.py`, `prompts.py`, `transcript_logger.py`, `model/build_db.py`.

If anything is unclear or you'd like a different scope (more examples, Windows-specific run scripts, or added tests), tell me which parts to expand and I will iterate.

## Key repository conventions (must follow exactly)
- User-facing language: Hinglish (brief Hindi+English). Lead confirmations/prompts are in Hinglish. See `prompts.py` for exact wording
- Lead storage: Lead JSON fields MUST be English (`name`, `email`, `company`, `interest`, `phone`, `budget`) — used for CRM downstream  
- Tools: all user-facing tools follow the decorator pattern: `@function_tool()`
- Conversation logging: streaming JSONL + session snapshots at `conversations/transcript_session_<timestamp>.json`
- RAG chunk settings: chunk_size=1500, overlap=200 (see `model/build_db.py`)
- Persona loading: Always from CRM API using extracted dialed number - no local fallbacks
- Voice configuration: Use `voices/all_voices.json` for TTS voice mapping via `instances.py` 
- Logging: Centralized via `logging_config.py` with third-party noise filtering (pymongo, werkzeug)
- Database: Optional MongoDB Atlas integration via `db_config.py` for leads/conversations
- Session management: Auto-hangup configurable via `AUTO_HANGUP_WAIT_SECONDS` and `HANGUP_ON_REQUEST_WAIT_SECONDS`
- Testing approach: Mix of pytest (integration tests) + direct Python scripts (component tests)

## Architecture & data flows
- Hybrid system: Fast JSON lookup in `data/` for basic queries → RAG fallback via `model/runapi.py` for deep queries (keywords: features/how to/api/integrate)
- Voice flow: STT → Agent (tools + RAG) → TTS. Realtime logging via `transcript_logger.py` (JSONL stream + session snapshots)
- Lead flow: `detect_lead_intent()` → `create_lead()` (validate → sanitize → write `leads/lead_YYYYMMDD_HHMMSS.json`)
- Integration: LiveKit server for real-time comms, Redis for SIP PSRPC, ChromaDB for vectors
- SIP telephony: Zoiper/softphone → livekit-sip (port 5060) → LiveKit server (port 7880) → voice agent. All services must connect to same Redis instance
- Logging architecture: Agent-level hooks capture STT chunks and session items → background worker writes to `conversations/transcripts.jsonl` → shutdown callback saves final snapshot
- **Dynamic persona loading flow**: SIP call → LiveKit room → `cagent.py` extracts dialed number → API call → persona config applied directly in agent
- **Session lifecycle**: `SessionManager` handles auto-hangup timers, conversation history, and graceful cleanup with configurable wait times
- **Local vs Cloud setup**: Self-hosted LiveKit has limitations - advanced audio filters and VAD features require LiveKit Cloud. Use basic configurations for local development

## Patterns & integration points
- Agent instrumentation: `cagent.py` uses `transcription_node()` for STT capture and background watcher for session history logging
- Plugin references: `backup_plugin_modifications/` holds patched stubs; `docker_scripts/apply_modifications.py` and `verify_modifications.py` apply/verify patches
- LiveKit: Token handling via `generate_livekit_token.py` for backend service integration
- RAG runtime: `model/runapi.py` handles embeddings, key rotation, queries to `model/chroma_db/`
- SIP setup: Create trunks via `lk sip inbound create` + dispatch rules via `lk sip dispatch create`. JSON configs in `sip-setup/inbound_trunk.json` and `sip-setup/sip_dispatch.json`
- **Agent flow**: `cagent.py` handles everything: number extraction from room, persona loading from API, validation, and conversation
- **Voice configuration**: `instances.py` loads voice mappings from `voices/all_voices.json`, supports multiple TTS providers (Cartesia, ElevenLabs, Sarvam)
- **MongoDB integration**: Optional via `db_config.py` - connection pooling, error handling, and data persistence for leads/conversations

## Debugging & tests
- Tests are small Python scripts (not pytest) — run directly for basic functionality
- Webhook testing: Use `pytest tests/test_handler.py tests/test_integration.py -v` for comprehensive persona loading flow testing
- Database testing: `pytest tests/test_mongodb_integration.py -v` for MongoDB connection and operations
- Component testing: `pytest tests/test_session_manager.py tests/test_persona_config.py -v` for individual modules
- Conversation logging: Check `conversations/transcripts.jsonl` for realtime events and `conversations/transcript_session_<timestamp>.json` for session snapshots
- After editing knowledge files, run `python model/build_db.py` to rebuild embeddings
- SIP debugging: Use `sngrep` for SIP traffic inspection, check Redis connection with `redis-cli ping`, verify room participants with `lk room participants --room friday-assistant-room`
- Webhook debugging: Test handler endpoints directly with curl or check Flask logs for persona API responses
- Session debugging: Check auto-hangup behavior with `AUTO_HANGUP_WAIT_SECONDS` and `HANGUP_ON_REQUEST_WAIT_SECONDS` env vars



## When changing behavior
- Add unit tests that exercise the `@function_tool()` functions and the lead creation/validation paths
- If you change RAG knowledge, rebuild DB and add a small integration test hitting `model/runapi.py`
- For webhook/persona loading changes, add tests to `tests/test_handler.py` for API interactions and `tests/test_integration.py` for end-to-end flows
- Test persona loading by dialing different numbers and verifying agent behavior matches expected persona configuration

## Repository cleanup & maintenance notes
- Keep `LIVEKIT_API_SECRET` only where tokens are minted; prefer backend as canonical token authority
- Leads and conversations contain PII — protect filesystem or move to secure DB; prefer atomic writes or file locks for concurrent processes
- SIP security: API keys in `livekit.yaml` and `sip-setup/config.yaml` must be identical. RTP ports 10000-20000 need firewall access
- Webhook service: `handler.py` must be running before SIP calls to ensure persona loading. Monitor Flask logs for API failures
- **Transcript deduplication**: Fixed multiple save mechanisms causing 3 transcript files per session - now uses duplicate prevention in `transcript_logger.py`
- **Audio performance**: Optimized Deepgram STT with `nova-3-general` model, `multi` language, and smart formatting for better real-time processing
- **Deepgram configuration**: Current working STT uses `nova-3-general` model with `multi` language support for optimal Hindi-English transcription
- **Local LiveKit limitations**: Advanced VAD features require LiveKit Cloud - use basic silero.VAD.load() for local setups to avoid "audio filter cannot be enabled" errors

## Files to inspect when working end-to-end
- Backend: `cagent.py`, `generate_livekit_token.py`, `tools.py`, `model/runapi.py`, `backup_plugin_modifications/`
- Webhook System: `handler.py` for persona loading service, `tests/test_handler.py` and `tests/test_integration.py` for testing
- SIP Setup: `sip-setup/config.yaml`, `livekit.yaml`, trunk/dispatch JSON configs
- Knowledge Base: `data/triotech_content.json`, `data/triotech_knowledge.txt`

When in doubt: prefer the backend as the canonical token service and add a read-only backend endpoint to surface leads if the frontend needs them.
