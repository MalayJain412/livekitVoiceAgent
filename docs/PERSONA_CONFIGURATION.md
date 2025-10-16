# Persona Configuration Guide

## Overview

The voice agent now supports two persona loading modes controlled by the `PERSONA_USE` environment variable:

- **Local Mode**: Uses hardcoded prompts from `prompts.py`
- **API Mode**: Loads dynamic personas from the CRM API

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# PERSONA_USE: Choose persona loading mode
# - "api": Load personas from CRM API (dynamic, per dialed number)  
# - "local": Use hardcoded prompts from prompts.py (static, consistent)
PERSONA_USE="api"

# Default caller number for API fallback (when no job metadata)
DEFAULT_CALLER="8655701159"
```

## Usage Modes

### 1. Local Mode (`PERSONA_USE="local"`)

**When to use:**
- Development and testing
- Consistent persona across all calls
- No dependency on external API
- Faster startup and response

**Behavior:**
- Uses `AGENT_INSTRUCTION` from `prompts.py` for agent behavior
- Uses `SESSION_INSTRUCTION` from `prompts.py` for conversation flow
- Persona name: `local_default`
- No API calls made

**Configuration:**
```bash
PERSONA_USE="local"
```

### 2. API Mode (`PERSONA_USE="api"`)

**When to use:**
- Production environment
- Different personas per phone number
- Dynamic persona loading
- Integration with CRM system

**Behavior:**
- First tries to load persona from job metadata (webhook-provided)
- Falls back to API call using `DEFAULT_CALLER` number
- Builds comprehensive agent instructions from persona components
- Uses conversation structure for session behavior

**Configuration:**
```bash
PERSONA_USE="api"
DEFAULT_CALLER="8655701159"
```

## Persona Component Mapping (API Mode)

| Persona Component | Usage | Result |
|------------------|-------|---------|
| `welcomeMessage` | → Agent Instructions | Always starts with persona greeting |
| `personality` | → Agent Instructions | Core persona identity |
| `closingMessage` | → Agent Instructions | Ends with persona farewell |
| `conversationStructure` | → Session Instructions | Workflow/behavior guidance |

## Testing

Run the test script to verify configuration:

```bash
python test_persona_config.py
```

## Implementation Details

### Code Structure

1. **Environment Detection**: `should_use_local_persona()` checks `PERSONA_USE`
2. **Local Config**: `get_local_persona_config()` returns hardcoded prompts
3. **API Fallback**: `load_persona_with_fallback()` handles mode selection
4. **Agent Creation**: `cagent.py` creates agent with appropriate instructions

### Logging

The system logs persona loading events:

```json
{
  "type": "persona_loaded_from_api",
  "persona_name": "piperbot",
  "source": "api_fallback", 
  "persona_use_mode": "api"
}
```

## Migration Guide

### From API-only to Configurable

No code changes needed in your main application. Simply:

1. Add `PERSONA_USE` to your `.env` file
2. Choose "local" or "api" based on your needs
3. Restart the agent

### Switching Modes

To switch between modes:

1. Update `.env`: `PERSONA_USE="local"` or `PERSONA_USE="api"`
2. Restart the voice agent
3. Verify in logs: "Using local hardcoded persona" or "Using API-based persona loading"

## Benefits

- **Flexibility**: Switch between local and API modes without code changes
- **Development**: Use local mode for consistent testing
- **Production**: Use API mode for dynamic persona loading
- **Debugging**: Easy to isolate persona-related issues
- **Performance**: Local mode eliminates API dependency

## Troubleshooting

### Local Mode Issues
- Check `prompts.py` for valid instructions
- Verify environment variable: `PERSONA_USE="local"`

### API Mode Issues  
- Check API connectivity and `DEFAULT_CALLER` number
- Verify persona exists in CRM for the dialed number
- Check logs for API response details

## Example Logs

**Local Mode:**
```
INFO: PERSONA_USE=local: Using local hardcoded persona
INFO: Persona Name: local_default
```

**API Mode:**
```
INFO: PERSONA_USE=api: Using API-based persona loading  
INFO: Loading persona from API using DEFAULT_CALLER: 8655701159
INFO: Persona Name: piperbot
```