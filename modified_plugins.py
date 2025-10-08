"""
FRIDAY AI: Modified Plugin Loader
This module loads plugins with conversation logging capabilities.
If plugins are already modified in venv, use those. Otherwise, apply runtime patches.
"""

def check_plugins_already_modified():
    """Check if plugins are already modified with conversation logging"""
    try:
        # Check Google LLM
        from livekit.plugins.google import llm as google_llm
        import inspect
        google_source = inspect.getsource(google_llm)
        google_modified = "FRIDAY AI:" in google_source
        
        # Check Cartesia TTS  
        from livekit.plugins.cartesia import tts as cartesia_tts
        cartesia_source = inspect.getsource(cartesia_tts)
        cartesia_modified = "FRIDAY AI:" in cartesia_source
        
        return google_modified, cartesia_modified
        
    except Exception as e:
        print(f"FRIDAY AI: Error checking plugin modifications: {e}")
        return False, False

def apply_patches_if_needed():
    """Apply patches only if plugins are not already modified"""
    google_modified, cartesia_modified = check_plugins_already_modified()
    
    if google_modified and cartesia_modified:
        print("FRIDAY AI: Plugins already modified with conversation logging!")
        return True
    
    if google_modified:
        print("FRIDAY AI: Google LLM already modified")
    elif cartesia_modified:
        print("FRIDAY AI: Cartesia TTS already modified")
    
    # Apply patches for unmodified plugins
    if not google_modified or not cartesia_modified:
        try:
            from plugin_patcher import patch_google_llm, patch_cartesia_tts
            
            success = True
            if not google_modified:
                success = success and patch_google_llm()
            if not cartesia_modified:
                success = success and patch_cartesia_tts()
                
            return success
        except ImportError:
            print("FRIDAY AI: Plugin patcher not available, using original plugins")
            return False
    
    return True

def create_llm(model, temperature=0.8):
    """Create LLM instance with conversation logging"""
    apply_patches_if_needed()
    
    try:
        from livekit.plugins import google
        return google.LLM(model=model, temperature=temperature)
    except ImportError as e:
        raise ImportError(f"Could not import Google LLM plugin: {e}")

def create_tts(model, language, voice):
    """Create TTS instance with conversation logging"""
    apply_patches_if_needed()
    
    try:
        from livekit.plugins import cartesia
        return cartesia.TTS(model=model, language=language, voice=voice)
    except ImportError as e:
        raise ImportError(f"Could not import Cartesia TTS plugin: {e}")