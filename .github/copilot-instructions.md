# Friday AI Voice Bot - Agent Guidelines

This is a sophisticated **LiveKit-based SIP telephony voice bot** with dynamic persona loading, metadata-driven file matching, and robust CRM upload workflows. Understanding the architecture and data flow patterns is critical for effective development.

## Core Architecture Overview

**Multi-Service Stack:** LiveKit Server (port 7880) + SIP Bridge (port 5060) + Redis + Docker Egress + Python Agent
- `cagent.py` - Main voice agent entrypoint with egress recording and campaign metadata collection
- `handler.py` - Webhook handler for participant events and agent dispatch
- `persona_handler.py` - Dynamic persona loading from CRM API: `https://devcrm.xeny.ai/apis/api/public/mobile/{number}`
- `session_manager.py` - Call lifecycle, transcript logging, and auto-hangup management
- `mobile_api.py` - Campaign metadata extraction and filename generation with embedded IDs
- `upload_cron.py` - Metadata-based batch upload system (primary upload mechanism)
- `crm_upload.py` - Two-step upload: recording file → call data with recording URL

**Critical Flow:** SIP call → LiveKit room → webhook → agent dispatch → persona loading → recording with egress_id → conversation → session save with metadata → batch upload via cron

## Essential Development Patterns

### Metadata-Driven File Management
- **Campaign metadata collection** via `mobile_api.py` extracts campaignId, voiceAgentId, clientId from dialed number
- **Egress ID propagation:** Critical to capture `egress_id` in `cagent.py` and add to `campaign_metadata['egressId']`
- **Filename embedding:** Files use pattern `transcript_session_{campaignId}_{voiceAgentId}_{sessionId}.json`
- **Multi-strategy matching:** Primary=metadata, fallback=egress mapping, last resort=phone/room pattern

### Session & Recording Lifecycle
```python
# Required pattern in cagent.py - preserve egress_id scope
egress_id = None  # Function level scope
info = await lkapi.egress.start_room_composite_egress(req)
egress_id = info.egress_id
campaign_metadata['egressId'] = egress_id  # Critical for file matching
session_manager.set_campaign_metadata(campaign_metadata)
```

### Upload Workflow (Batch-First Strategy)
- **Primary mechanism:** `upload_cron.py` - runs every 5 minutes, metadata-based matching
- **File processing:** Conversation → find recording via egress → upload recording → upload call data
- **Egress mapping:** Read `recordings/EG_{id}.json` to get recording filename from LiveKit metadata
- **Fallback matching:** Phone number pattern matching when direct metadata fails

### Persona-Driven Configuration
- **NEVER use hardcoded instructions** - all agent behavior comes from CRM API via `persona_handler.py`
- Number extraction follows strict priority: `dialedNumber` attribute → SIP URI → room name pattern
- Persona validation in `validation.py` handles timezone/availability rules
- Three instruction types: `agent_instructions` (core identity), `session_instructions` (initial flow), `closing_message` (pre-hangup)

### Service Instance Configuration
Use `instances.py` for all AI services - supports dynamic voice selection:
```python
# Always use this pattern for service instances
instances = get_instances_from_payload(full_config)
session = AgentSession(stt=instances["stt"], llm=instances["llm"], tts=instances["tts"], vad=instances["vad"])
```

### Conversation Flow & Tools
- **Lead generation workflow:** `detect_lead_intent` → gather details → confirm in English → ask permission in Hinglish → `create_lead`
- **Critical rule:** Never call `end_call` in same turn as `create_lead` - must wait for user response
- Hangup detection via `HangupTool` and configurable phrases in `session_manager.py`
- Always check "Is there anything else?" before ending calls

### Session Management
```python
# Required session setup pattern
session_manager = SessionManager(session)
await session_manager.setup_session_logging()
await session_manager.setup_shutdown_callback()
await session_manager.start_history_watcher()
```

## Critical File Relationships

- **Config chain:** `.env` → `config.py` → `instances.py` → service creation
- **Persona chain:** Dialed number → `persona_handler.py` → CRM API → dynamic instructions
- **Logging chain:** `session_manager.py` → `transcript_logger.py` → MongoDB/file storage → CRM upload
- **Call flow:** `handler.py` webhook → agent dispatch → `cagent.py` entrypoint → persona loading → conversation
- **Upload chain:** `cagent.py` egress → `upload_cron.py` metadata matching → `crm_upload.py` two-step upload

## Essential Commands & Testing

**Production deployment:**
```bash
# Start all services (run each in separate screen sessions)
livekit-server --config sip-setup/livekit.yaml
livekit-sip --config sip-setup/config.yaml  
docker run -d --name livekit-egress --network="host" -v $(pwd)/recordings:/recordings livekit/egress
python cagent.py
```

**Upload workflows:**
```bash
# Primary batch upload (recommended for production)
python upload_cron.py --dry-run --verbose
python upload_cron.py --batch-size=10
# Cron scheduling: */5 * * * * cd /path && python upload_cron.py >> upload_cron.log 2>&1

# Manual upload by egress ID
python scripts/upload_by_egress.py EG_HKwnFWVEqPfd
python scripts/bulk_upload_all_egress.py
```

**Development testing:**
- Use `TEST_API_RESPONSE_FILE` env var to load test persona configs locally
- Test persona loading: `python -c "from persona_handler import load_persona_from_api; print(load_persona_from_api('+918655048643'))"`
- Check webhook flow: `curl -X POST localhost:8080/livekit-webhook -d @test_participant.json`

## Common Integration Points

### MongoDB Integration
- Dual storage: MongoDB (primary) + file fallback in `leads/` and `conversations/`
- Use `USE_MONGODB=false` to disable and force file storage
- All DB operations through `db_config.py` abstractions

### Voice/TTS Configuration  
- Voice mappings in `voices/all_voices.json` - supports Cartesia, ElevenLabs, Sarvam, Azure
- Provider-specific voice ID resolution in `instances.py`
- Language detection and voice matching from persona config

### Transcript Management
- Real-time logging via `transcript_logger.py` with structured events
- Automatic session history extraction in `session_manager.py`
- CRM upload via `crm_upload.py` if enabled with campaign mapping

## Key Conventions

- **Error handling:** Always provide fallback instructions - never let missing persona config crash sessions
- **Language patterns:** Mirror user language (Hindi/English/Hinglish), feminine verb forms for agent
- **Logging:** Use structured events with timestamps, never log sensitive data in plain text
- **Configuration:** Environment-first, API-driven, no hardcoded business logic
- **Session lifecycle:** Setup → persona loading → conversation → transcript save → CRM upload

## Security Notes

- SIP credentials in `sip-setup/config.yaml` (username: 1001, password: 1001)
- LiveKit API keys in `.env` - never commit these
- MongoDB credentials via `MONGODB_URI` environment variable
- CRM API tokens for persona loading and lead upload

This architecture enables multi-tenant voice bots with dynamic personalities, comprehensive call analytics, and seamless CRM integration - maintain these patterns when extending functionality.