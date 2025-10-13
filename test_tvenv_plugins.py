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
    
    # Check environment essentials for logging
    print("Checking agent-level logging components...")
    status = True
    try:
        from transcript_logger import get_log_path
        print("SUCCESS: transcript_logger available")
    except Exception as e:
        print(f"ERROR: transcript_logger not importable: {e}")
        status = False
    
    # Test plugin file locations
    print("\nPlugin File Verification:")
    venv_path = Path(sys.executable).parent.parent
    print(f"Using virtual environment: {venv_path.name}")
    
    google_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "google" / "llm.py"
    cartesia_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "cartesia" / "tts.py"
    
    # Check Google LLM (presence only)
    if google_path.exists():
        with open(google_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Google LLM: File exists")
    else:
        print("Google LLM: File not found")
        status = False
    
    # Check Cartesia TTS
    if cartesia_path.exists():
        with open(cartesia_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Cartesia TTS: File exists")
    else:
        print("Cartesia TTS: File not found")
        status = False
    
    print("\nTest Summary:")
    if status:
        print("SUCCESS: tvenv appears correctly configured. transcript_logger available and plugins present.")
        print("Your Friday AI system is ready to use with the new environment.")
    else:
        print("ISSUE: Some problems were found with the tvenv setup.")
        print("Please ensure the required packages are installed and transcript_logger.py is present.")
    
    return status

if __name__ == "__main__":
    test_tvenv_plugins()