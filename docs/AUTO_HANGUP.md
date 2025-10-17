# Automatic Call Hangup Feature

The Friday AI agent includes automatic call hangup functionality that can end calls in two scenarios:

1. **After Closing Message**: When the agent says its configured closing message and the user doesn't respond
2. **On Explicit User Request**: When the user explicitly asks to hang up the call

## Configuration

### Environment Variables

Set these environment variables to configure the behavior:

```powershell
# Time to wait after assistant closing message (seconds, default: 4)
$env:AUTO_HANGUP_WAIT_SECONDS = "4"

# Time to wait after explicit user hangup request (seconds, default: 2)  
$env:HANGUP_ON_REQUEST_WAIT_SECONDS = "2"

# Custom hangup phrases (comma-separated, optional)
$env:HANGUP_PHRASES = "please hang up,end call,disconnect,terminate call"
```

### Default Hangup Phrases

If `HANGUP_PHRASES` is not set, these default phrases are used:
- "please hang up"
- "hang up the call" 
- "hang up"
- "please hangup"
- "end the call"
- "disconnect the call"
- "terminate the call"
- "please disconnect"
- "cut the call"
- "finish the call"

## How It Works

### Closing Message Detection
1. The agent's persona includes a configured `closing_message`
2. When the agent speaks this closing message, a timer starts
3. If no user activity occurs within `AUTO_HANGUP_WAIT_SECONDS`, the call is ended
4. Any user activity (speech) cancels the timer

### Explicit User Request
1. User speech is monitored for hangup phrases
2. When detected, a shorter timer starts (`HANGUP_ON_REQUEST_WAIT_SECONDS`)
3. The call is ended after the shorter wait period

### Call Termination
- Uses LiveKit's `delete_room` API to end the call for all participants
- Logs an `auto_hangup` event to the transcript for monitoring

## Testing Locally

### Basic Test
```powershell
# Set short timers for testing
$env:AUTO_HANGUP_WAIT_SECONDS = "3"
$env:HANGUP_ON_REQUEST_WAIT_SECONDS = "1"

# Run the agent
python cagent.py dev
```

### Custom Phrases Test
```powershell
# Set custom hangup phrases
$env:HANGUP_PHRASES = "bye bye,goodbye,end this call"

python cagent.py dev
```

## Monitoring and Logs

### Log Messages to Look For

The SessionManager logs key events with the prefix "SessionManager:":

```
INFO - SessionManager: detected closing message — scheduling auto-hangup in 4s unless user replies
INFO - SessionManager: explicit user hangup request detected (matched phrase) — scheduling immediate hangup wait  
INFO - SessionManager: user activity detected — cancelling pending auto-hangup
INFO - SessionManager: auto-hangup wait started for room=friday-assistant-room
INFO - SessionManager: no user reply detected for 4s after closing — performing auto-hangup for room friday-assistant-room
```

### Transcript Events

Auto-hangup events are logged to `conversations/transcripts.jsonl`:

```json
{
  "type": "auto_hangup",
  "reason": "closing_message_no_reply", 
  "room": "friday-assistant-room",
  "timestamp": "2025-10-17T15:33:48Z"
}
```

### Troubleshooting

**Call not hanging up automatically:**
1. Check that the persona has a `closing_message` configured
2. Verify the agent actually spoke the closing message (check transcripts)
3. Look for "SessionManager: detected closing message" in logs
4. Check if user activity cancelled the timer

**Hangup phrases not working:**
1. Verify phrases are configured correctly (case-insensitive)
2. Check logs for "explicit user hangup request detected" 
3. Ensure phrases are exact substring matches

**Permission errors:**
1. Verify LiveKit API credentials and permissions
2. Check for "Failed to auto hangup room" error messages

## Running Tests

```powershell
# Run all auto-hangup tests
python -m pytest tests/test_session_manager.py -v

# Run specific test
python -m pytest tests/test_session_manager.py::test_hangup_executes_when_no_activity -v
```

## Implementation Files

- `session_manager.py` - Main implementation
- `tests/test_session_manager.py` - Unit and integration tests
- `docs/AUTO_HANGUP.md` - This documentation