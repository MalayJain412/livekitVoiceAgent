# FRIDAY AI: Plugin Management Solution

## Problem (Historical)
When doing `pip install` or reinstalling dependencies, the modified LiveKit plugins in the venv get overwritten with the original versions, losing the conversation logging functionality.

## Current Solution (Recommended)
**Agent-Level Logging** - No plugin modifications required:

1. **Realtime JSONL Logging**: `transcript_logger.py` provides a background worker that writes conversation events to `conversations/transcripts.jsonl` as they happen.
2. **Agent Instrumentation**: `cagent.py` uses LiveKit Agent API hooks to capture STT chunks via `transcription_node()` and session items via background watcher.
3. **Session Snapshots**: Job shutdown callback writes pretty JSON snapshots to `conversations/transcript_session_<timestamp>.json`.
4. **Zero Plugin Edits**: No modifications to files in the virtual environment required.

## Deprecated Approach (Archived)
The repository previously included a hybrid plugin-patching approach (runtime patching + backup/restore) to add conversation logging into third-party plugins. **This approach is deprecated** due to fragility and upgrade issues.

## Current Architecture Files

### 1. `transcript_logger.py`
- **Purpose**: Background JSONL writer for realtime conversation logging
- **Usage**: Called by agent hooks to log STT chunks and conversation items
- **Features**: 
  - Non-blocking queue-based writer
  - Appends to `conversations/transcripts.jsonl`
  - Defensive error handling to never break agent pipeline

### 2. `cagent.py`
- **Purpose**: Main voice agent with integrated logging hooks
- **Features**: 
  - `transcription_node()` captures streaming STT chunks
  - Background watcher polls `session.history` and logs committed items
  - Shutdown callback writes session snapshot and flushes logger
  - Uses standard LiveKit plugins directly (google, cartesia)

### 3. `config.py`
- **Purpose**: Minimal helper for conversations directory setup
- **Changes**: No longer creates legacy conversation files
- **Usage**: Ensures `conversations/` directory exists

## Usage Instructions

### For Regular Development
Just use the application normally - logging is automatic:
```powershell
# Realtime logging happens automatically
python cagent.py
```

### After pip install / requirements.txt update
No action required. The agent-level logging mechanism works without patching vendor packages.

### For Docker Deployment
Use the existing `docker_scripts/apply_modifications.py` which applies the backup plugin files if needed for reference.

## How It Works

### 1. Agent-Level Hooks
```python
# cagent.py uses LiveKit Agent API directly
async def transcription_node(self, text, model_settings):
    async for chunk in text:
        # Log STT chunks as they arrive
        log_user_message(content, source="transcription_node", meta=meta)
        yield chunk
```

### 2. Background Logging
The logging system:
- Runs a background thread with queue-based JSONL writer
- Captures STT chunks via `transcription_node()` 
- Watches `session.history` for committed conversation items
- Never blocks the agent pipeline

### 3. Session Management
On job shutdown:
- Agent saves final session snapshot as pretty JSON
- Background logger is flushed and stopped gracefully
- All conversation data preserved in two formats (JSONL + snapshot)

## Integration with Existing Code

### Current Approach (Agent-Level)
```python
from livekit.plugins import google, cartesia
from transcript_logger import log_user_message, log_event

# Use plugins directly - no wrappers needed
llm = google.LLM(model="gemini-2.5-flash", temperature=0.8)
tts = cartesia.TTS(model="sonic-2", language="hi", voice="...")

# Logging happens via agent hooks, not plugin modifications
```

## Maintenance Workflow

### 1. Development
- Just code normally - conversation logging is automatic via agent hooks
- Check `conversations/transcripts.jsonl` for realtime events
- Check `conversations/transcript_session_*.json` for session snapshots

### 2. After Dependencies Update
```powershell
pip install -r requirements.txt
# No additional steps required - agent-level logging is dependency-independent
```

### 3. Docker Deployment
```bash
# Standard deployment - no special plugin handling needed
# Optional: use docker_scripts/apply_modifications.py for backup plugin reference
```

## Benefits

1. **Zero Dependencies**: No plugin modifications or backup/restore scripts needed
2. **Upgrade-Safe**: Survives any pip installs or LiveKit version updates automatically  
3. **Non-Invasive**: Uses official LiveKit Agent API hooks only
4. **Realtime**: JSONL streaming provides immediate visibility into conversations
5. **Maintainable**: All logging code in repo, no external file dependencies

## Files to Keep in Version Control

- ✅ `transcript_logger.py` (realtime JSONL writer) 
- ✅ `cagent.py` (agent entrypoint and logging hooks)
- ✅ `docs/` and `backup_plugin_modifications/` for historical reference
- ✅ `conversations/` directory (auto-created, contains logs)

## Testing

Test the system works:
```powershell
# Start agent and check logging
python cagent.py

# In another terminal, check realtime logging
Get-Content conversations\transcripts.jsonl -Wait
```

## Troubleshooting

### Issue: "No conversation logging visible"
**Solution**: Check that `conversations/transcripts.jsonl` is being written to and agent hooks are registered

### Issue: "ImportError when starting agent"
**Solution**: Check that LiveKit plugins are installed:
```powershell
pip install livekit-plugins-google livekit-plugins-cartesia livekit-plugins-deepgram livekit-plugins-silero
```

### Issue: "JSONL file not updating"
**Solution**: Check transcript_logger background thread:
```python
from transcript_logger import get_log_path
print(get_log_path())  # Should show conversations/transcripts.jsonl path
```

## Summary

This solution provides a robust, maintainable way to ensure conversation logging works regardless of how the environment is set up. It automatically adapts to different scenarios and provides tools for easy maintenance.

### Local Dev & SIP Automation (cross-reference)

For quick local development and SIP provisioning the canonical `README.md` includes the recommended commands:

1. Start services in detached `screen` sessions (LiveKit server, SIP bridge, backend agent).
2. Automate SIP trunk creation and dispatch with the `lk` CLI and `jq`/`sed` to avoid manual ID copy/paste:

```bash
TRUNK_ID=$(lk sip inbound create --project friday sip-setup/inbound_trunk.json | jq -r '.sip_trunk_id')
sed -i "s/REPLACE_WITH_TRUNK_ID/$TRUNK_ID/g" sip-setup/sip_dispatch.json
lk sip dispatch create --project friday sip-setup/sip_dispatch.json
```

Refer to `README.md` for exact paths and additional verification steps.