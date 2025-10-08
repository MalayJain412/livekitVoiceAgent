#!/usr/bin/env python
"""
FRIDAY AI: tvenv Plugin Verification Test
Test script to verify that plugins in the new tvenv have conversation logging.
"""

import sys
from pathlib import Path

def test_tvenv_plugins():
    """Test that tvenv plugins have conversation logging"""
    
    print("FRIDAY AI: tvenv Plugin Verification")
    print("=" * 40)
    
    # Test imports
    try:
        from modified_plugins import check_plugins_already_modified, create_llm, create_tts
        print("SUCCESS: Plugin management functions imported")
    except ImportError as e:
        print(f"ERROR: Could not import plugin functions: {e}")
        return False
    
    # Check plugin modifications
    try:
        google_modified, cartesia_modified = check_plugins_already_modified()
        print(f"Google LLM has conversation logging: {google_modified}")
        print(f"Cartesia TTS has conversation logging: {cartesia_modified}")
        
        if google_modified and cartesia_modified:
            print("SUCCESS: Both plugins have conversation logging!")
            status = True
        else:
            print("WARNING: Not all plugins have conversation logging")
            status = False
    except Exception as e:
        print(f"ERROR: Could not check plugin modifications: {e}")
        return False
    
    # Test plugin file locations
    print("\nPlugin File Verification:")
    venv_path = Path(sys.executable).parent.parent
    print(f"Using virtual environment: {venv_path.name}")
    
    google_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "google" / "llm.py"
    cartesia_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "cartesia" / "tts.py"
    
    # Check Google LLM
    if google_path.exists():
        with open(google_path, 'r', encoding='utf-8') as f:
            content = f.read()
        has_friday_ai = "FRIDAY AI:" in content
        print(f"Google LLM: File exists, FRIDAY AI mods: {has_friday_ai}")
    else:
        print("Google LLM: File not found")
        status = False
    
    # Check Cartesia TTS
    if cartesia_path.exists():
        with open(cartesia_path, 'r', encoding='utf-8') as f:
            content = f.read()
        has_friday_ai = "FRIDAY AI:" in content
        print(f"Cartesia TTS: File exists, FRIDAY AI mods: {has_friday_ai}")
    else:
        print("Cartesia TTS: File not found")
        status = False
    
    print("\nTest Summary:")
    if status:
        print("SUCCESS: tvenv is properly configured with conversation logging!")
        print("Your Friday AI system is ready to use with the new environment.")
    else:
        print("ISSUE: Some problems were found with the tvenv setup.")
        print("You may need to run: python setup_plugins.py")
    
    return status

if __name__ == "__main__":
    test_tvenv_plugins()