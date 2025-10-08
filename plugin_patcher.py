"""
FRIDAY AI: Plugin Patcher
This module dynamically patches the original LiveKit plugins with conversation logging.
"""

import os
import sys
import inspect
from pathlib import Path
from datetime import datetime
import json

def patch_google_llm():
    """Patch the Google LLM plugin with conversation logging"""
    try:
        from livekit.plugins.google import llm as google_llm
        
        # Store original _run method
        original_run = google_llm.LLMStream._run
        
        def _log_user_message(content: str) -> None:
            """Log user message to conversation JSON file"""
            try:
                # Get project root (same logic as in config.py)
                project_root = Path(__file__).parent
                
                # Find most recent conversation log
                conversations_dir = project_root / "conversations"
                if not conversations_dir.exists():
                    conversations_dir.mkdir()
                    return
                
                conversation_files = list(conversations_dir.glob("conversation_*.json"))
                if not conversation_files:
                    return
                
                # Get the most recent conversation file
                latest_conversation = max(conversation_files, key=lambda p: p.stat().st_mtime)
                
                # Read existing data
                try:
                    with open(latest_conversation, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {"conversation": []}
                
                # Add user message
                user_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "user",
                    "content": content,
                    "source": "llm_plugin"
                }
                
                data["conversation"].append(user_entry)
                
                # Write back to file
                with open(latest_conversation, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
                print(f"FRIDAY AI: Logged user message to {latest_conversation.name}")
                
            except Exception as e:
                print(f"FRIDAY AI: Error logging user message: {e}")
        
        async def patched_run(self):
            """Patched _run method with user input logging"""
            # FRIDAY AI: Log user input at the start
            try:
                for turn in reversed(self._chat_ctx.turns):
                    if turn.role == "user" and turn.parts:
                        for part in turn.parts:
                            if part.text and part.text.strip():
                                _log_user_message(part.text.strip())
                                break
                        break
            except Exception as e:
                print(f"FRIDAY AI: Error in user logging: {e}")
            
            # Call original method
            return await original_run(self)
        
        # Apply the patch
        google_llm.LLMStream._run = patched_run
        print("FRIDAY AI: Successfully patched Google LLM with conversation logging")
        return True
        
    except Exception as e:
        print(f"FRIDAY AI: Error patching Google LLM: {e}")
        return False

def patch_cartesia_tts():
    """Patch the Cartesia TTS plugin with conversation logging"""
    try:
        from livekit.plugins.cartesia import tts as cartesia_tts
        
        # Store original methods
        original_chunked_run = cartesia_tts.ChunkedStream._run
        original_stream_run = cartesia_tts.SynthesizeStream._run
        
        def _log_tts_message(text: str) -> None:
            """Log TTS message to conversation JSON file"""
            try:
                # Get project root (same logic as in config.py)
                project_root = Path(__file__).parent
                
                # Find most recent conversation log
                conversations_dir = project_root / "conversations"
                if not conversations_dir.exists():
                    conversations_dir.mkdir()
                    return
                
                conversation_files = list(conversations_dir.glob("conversation_*.json"))
                if not conversation_files:
                    return
                
                # Get the most recent conversation file
                latest_conversation = max(conversation_files, key=lambda p: p.stat().st_mtime)
                
                # Read existing data
                try:
                    with open(latest_conversation, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {"conversation": []}
                
                # Add agent message
                agent_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "agent",
                    "content": text,
                    "source": "tts_plugin"
                }
                
                data["conversation"].append(agent_entry)
                
                # Write back to file
                with open(latest_conversation, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
                print(f"FRIDAY AI: Logged agent message to {latest_conversation.name}")
                
            except Exception as e:
                print(f"FRIDAY AI: Error logging agent message: {e}")
        
        async def patched_chunked_run(self, output_emitter):
            """Patched ChunkedStream._run with TTS logging"""
            # FRIDAY AI: Log TTS output
            try:
                if hasattr(self, '_input_text') and self._input_text.strip():
                    _log_tts_message(self._input_text.strip())
            except Exception as e:
                print(f"FRIDAY AI: Error in TTS logging: {e}")
            
            # Call original method
            return await original_chunked_run(self, output_emitter)
        
        async def patched_stream_run(self, output_emitter):
            """Patched SynthesizeStream._run with TTS logging"""
            # Initialize logged text tracking
            if not hasattr(self, '_logged_text'):
                self._logged_text = ""
            
            # FRIDAY AI: Track input text for logging
            try:
                # Accumulate text from input stream
                accumulated_text = ""
                original_push_text = self.push_text
                
                def patched_push_text(token: str) -> None:
                    nonlocal accumulated_text
                    accumulated_text += token
                    return original_push_text(token)
                
                self.push_text = patched_push_text
                
                # Call original method
                result = await original_stream_run(self, output_emitter)
                
                # Log accumulated text
                if accumulated_text.strip():
                    _log_tts_message(accumulated_text.strip())
                
                return result
                
            except Exception as e:
                print(f"FRIDAY AI: Error in streaming TTS logging: {e}")
                # Fall back to original method
                return await original_stream_run(self, output_emitter)
        
        # Apply patches
        cartesia_tts.ChunkedStream._run = patched_chunked_run
        cartesia_tts.SynthesizeStream._run = patched_stream_run
        print("FRIDAY AI: Successfully patched Cartesia TTS with conversation logging")
        return True
        
    except Exception as e:
        print(f"FRIDAY AI: Error patching Cartesia TTS: {e}")
        return False

def apply_all_patches():
    """Apply all conversation logging patches"""
    print("FRIDAY AI: Applying conversation logging patches...")
    
    google_success = patch_google_llm()
    cartesia_success = patch_cartesia_tts()
    
    if google_success and cartesia_success:
        print("FRIDAY AI: All patches applied successfully!")
        return True
    elif google_success or cartesia_success:
        print("FRIDAY AI: Some patches applied successfully")
        return True
    else:
        print("FRIDAY AI: Failed to apply patches - conversation logging disabled")
        return False

def get_original_classes():
    """Get the original plugin classes"""
    try:
        from livekit.plugins import google, cartesia
        return google.LLM, cartesia.TTS
    except ImportError as e:
        print(f"FRIDAY AI: Error importing original plugins: {e}")
        return None, None