# FRIDAY AI: Plugin Management Solution

## Problem
When doing `pip install` or reinstalling dependencies, the modified LiveKit plugins in the venv get overwritten with the original versions, losing the conversation logging functionality.

## Solution Overview
We've implemented a **hybrid approach** that:
1. **Uses modified plugins** if they exist in the venv
2. **Applies runtime patches** if original plugins are detected
3. **Provides backup and restore utilities** for easy maintenance

## Files Created

### 1. `modified_plugins.py`
- **Purpose**: Main interface for creating LLM and TTS instances with conversation logging
- **Usage**: Import `create_llm()` and `create_tts()` instead of using original plugins directly
- **Features**: 
  - Automatically detects if plugins are already modified
  - Falls back to runtime patching if needed
  - Provides clean API for the rest of the application

### 2. `plugin_patcher.py`
- **Purpose**: Runtime patching system for original plugins
- **Usage**: Automatically called by `modified_plugins.py` when needed
- **Features**:
  - Patches Google LLM to log user input
  - Patches Cartesia TTS to log agent responses
  - Non-invasive - doesn't modify files on disk

### 3. `setup_plugins.py`
- **Purpose**: Maintenance script for plugin management
- **Usage**: Run after `pip install` to restore modifications
- **Features**:
  - Backs up current modifications
  - Restores from backup when needed
  - Can be run manually or in build scripts

### 4. Updated `cagent.py`
- **Purpose**: Main application using the new plugin system
- **Changes**: 
  - Imports `create_llm()` and `create_tts()` from `modified_plugins`
  - No longer directly imports original plugins
  - Automatically gets conversation logging

## Usage Instructions

### For Regular Development
Just use the application normally:
```python
# This now automatically includes conversation logging
python cagent.py
```

### After pip install / requirements.txt update
Run the setup script:
```powershell
python setup_plugins.py
```

### For Docker Deployment
Use the existing `docker_scripts/apply_modifications.py` which applies the backup files.

## How It Works

### 1. Plugin Detection
```python
from modified_plugins import create_llm, create_tts

# These functions automatically:
# 1. Check if plugins are already modified
# 2. Apply runtime patches if needed
# 3. Return instances with conversation logging
```

### 2. Runtime Patching
If original plugins are detected, the system:
- Patches `google.LLM.LLMStream._run()` to log user input
- Patches `cartesia.TTS.ChunkedStream._run()` and `SynthesizeStream._run()` to log agent responses
- Applies patches at runtime without modifying files

### 3. Backup Management
The backup system:
- Stores modified plugins in `backup_plugin_modifications/`
- Can restore modifications after pip installs
- Preserves conversation logging functionality

## Integration with Existing Code

### Before
```python
from livekit.plugins import google, cartesia

llm = google.LLM(model="gemini-2.5-flash", temperature=0.8)
tts = cartesia.TTS(model="sonic-2", language="hi", voice="...")
```

### After
```python
from modified_plugins import create_llm, create_tts

llm = create_llm(model="gemini-2.5-flash", temperature=0.8)
tts = create_tts(model="sonic-2", language="hi", voice="...")
```

## Maintenance Workflow

### 1. Development
- Just code normally - conversation logging is automatic
- No need to manually modify plugin files

### 2. After Dependencies Update
```powershell
pip install -r requirements.txt
python setup_plugins.py  # Restore conversation logging
```

### 3. Docker Deployment
```bash
# Use existing docker script
python docker_scripts/apply_modifications.py
```

## Benefits

1. **Automatic**: No manual file editing required
2. **Persistent**: Survives pip installs when using setup script
3. **Flexible**: Works with runtime patching as fallback
4. **Clean**: Doesn't clutter the main application code
5. **Maintainable**: Single point of control for plugin modifications

## Files to Keep in Version Control

- ✅ `modified_plugins.py`
- ✅ `plugin_patcher.py` 
- ✅ `setup_plugins.py`
- ✅ `backup_plugin_modifications/` (entire folder)
- ❌ Don't commit modified venv files

## Testing

Test the system works:
```python
# Test that conversation logging is available
from modified_plugins import check_plugins_already_modified
google_modified, cartesia_modified = check_plugins_already_modified()
print(f"Google: {google_modified}, Cartesia: {cartesia_modified}")
```

## Troubleshooting

### Issue: "No conversation logging after pip install"
**Solution**: Run `python setup_plugins.py`

### Issue: "ImportError when creating LLM/TTS"
**Solution**: Check that LiveKit plugins are installed:
```powershell
pip install livekit-plugins-google livekit-plugins-cartesia
```

### Issue: "Patches not applying"
**Solution**: Check if backup files exist:
```python
ls backup_plugin_modifications/
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