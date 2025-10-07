# Friday AI Assistant - Plugin Modifications Backup

This directory contains backup copies of the modified plugin files for the Friday AI Assistant hybrid conversation logging system.

## 📋 **Files Included:**

### 1. `google_llm_modified.py`
- **Original Location**: `venv/Lib/site-packages/livekit/plugins/google/llm.py`
- **Purpose**: User input capture at LLM level
- **Modifications**:
  - Added `sys` and `datetime` imports
  - Added `_log_user_message()` function
  - Added user input logging in `LLMStream._run()` method

### 2. `cartesia_tts_modified.py`
- **Original Location**: `venv/Lib/site-packages/livekit/plugins/cartesia/tts.py`
- **Purpose**: Agent response capture at TTS level
- **Modifications**:
  - Added `sys` and `datetime` imports
  - Added `_log_tts_message()` function
  - Added logging in `ChunkedStream._run()` method
  - Added logging in `SynthesizeStream._input_task()` method
  - Added `_logged_text` tracking variable

## 🔧 **How to Restore Changes:**

### Method 1: Copy-Paste Approach
1. **For Google LLM Plugin**:
   ```bash
   # Copy the modified functions and imports from google_llm_modified.py
   # Paste into: venv/Lib/site-packages/livekit/plugins/google/llm.py
   ```

2. **For Cartesia TTS Plugin**:
   ```bash
   # Copy the modified functions and imports from cartesia_tts_modified.py
   # Paste into: venv/Lib/site-packages/livekit/plugins/cartesia/tts.py
   ```

### Method 2: File Replacement (Advanced)
```bash
# Backup original files first
cp venv/Lib/site-packages/livekit/plugins/google/llm.py venv/Lib/site-packages/livekit/plugins/google/llm.py.original
cp venv/Lib/site-packages/livekit/plugins/cartesia/tts.py venv/Lib/site-packages/livekit/plugins/cartesia/tts.py.original

# Replace with modified versions (adjust paths as needed)
cp backup_plugin_modifications/google_llm_modified.py venv/Lib/site-packages/livekit/plugins/google/llm.py
cp backup_plugin_modifications/cartesia_tts_modified.py venv/Lib/site-packages/livekit/plugins/cartesia/tts.py
```

## 🎯 **Key Changes Summary:**

### User Input Logging (LLM Level):
```python
# Added in google/llm.py
def _log_user_message(content: str) -> None:
    # Logs user messages from LLM to capture both voice and text input

# Integration point in LLMStream._run():
for turn in reversed(turns):
    if turn.role == "user" and turn.parts:
        for part in turn.parts:
            if part.text and part.text.strip():
                _log_user_message(part.text.strip())
                break
        break
```

### Agent Response Logging (TTS Level):
```python
# Added in cartesia/tts.py
def _log_tts_message(text: str) -> None:
    # Logs agent responses from TTS to capture complete, clean text

# Integration points:
# 1. ChunkedStream._run(): _log_tts_message(self._input_text)
# 2. SynthesizeStream._input_task(): Accumulates and logs complete text
```

## 🔍 **Identification Comments:**

All modifications are marked with `# FRIDAY AI:` comments for easy identification:
- Header comments in both files indicate Friday AI Assistant modifications
- Import additions marked with `# FRIDAY AI: Added for...`
- Function additions marked with `# FRIDAY AI: Added ... function`
- Integration points marked with `# FRIDAY AI: ... (Hybrid logging approach)`

## ⚠️ **Important Notes:**

1. **Dependencies**: These modifications require the `config.py` file in the project root
2. **Path Adjustments**: The backup files may need path adjustments when copying
3. **Version Compatibility**: These modifications are based on the current LiveKit plugin versions
4. **Testing**: Always test after restoring modifications to ensure proper functionality

## 📚 **Related Documentation:**

- `HYBRID_CONVERSATION_LOGGING.md` - Complete implementation documentation
- `CONVERSATION_LOGGING_JSON_IMPLEMENTATION.md` - Original plugin-level approach
- `config.py` - Required configuration file for logging

## 🔄 **Update Process:**

When LiveKit plugins are updated:
1. **Backup current modifications** using these files
2. **Update LiveKit packages** as needed
3. **Reapply modifications** using these backup files as reference
4. **Test functionality** to ensure compatibility

---

**Created**: August 18, 2025  
**Purpose**: Backup and documentation for Friday AI Assistant plugin modifications  
**Approach**: Hybrid conversation logging (LLM + TTS)
