"""
FRIDAY AI: Plugin Setup Script
This script ensures conversation logging is available after pip installs.
Run this after any pip install or requirements.txt update.
"""

import os
import sys
import shutil
from pathlib import Path

def backup_current_plugins():
    """Backup current modified plugins before potential overwrite"""
    try:
        venv_path = Path(sys.executable).parent.parent
        google_llm_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "google" / "llm.py"
        cartesia_tts_path = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "cartesia" / "tts.py"
        
        backup_dir = Path(__file__).parent / "backup_plugin_modifications"
        backup_dir.mkdir(exist_ok=True)
        
        # Backup Google LLM if it contains Friday AI modifications
        if google_llm_path.exists():
            with open(google_llm_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if "FRIDAY AI:" in content:
                backup_path = backup_dir / "google_llm_modified.py"
                shutil.copy2(google_llm_path, backup_path)
                print(f"Backed up modified Google LLM to {backup_path}")
        
        # Backup Cartesia TTS if it contains Friday AI modifications
        if cartesia_tts_path.exists():
            with open(cartesia_tts_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if "FRIDAY AI:" in content:
                backup_path = backup_dir / "cartesia_tts_modified.py"
                shutil.copy2(cartesia_tts_path, backup_path)
                print(f"Backed up modified Cartesia TTS to {backup_path}")
        
        return True
    except Exception as e:
        print(f"Error backing up plugins: {e}")
        return False

def restore_modified_plugins():
    """Restore modified plugins from backup"""
    try:
        venv_path = Path(sys.executable).parent.parent
        backup_dir = Path(__file__).parent / "backup_plugin_modifications"
        
        if not backup_dir.exists():
            print("No backup directory found - using runtime patching instead")
            return False
        
        # Restore Google LLM
        google_backup = backup_dir / "google_llm_modified.py"
        google_target = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "google" / "llm.py"
        
        if google_backup.exists() and google_target.exists():
            # Check if target needs updating
            with open(google_target, 'r', encoding='utf-8') as f:
                target_content = f.read()
            
            if "FRIDAY AI:" not in target_content:
                shutil.copy2(google_backup, google_target)
                print(f"Restored modified Google LLM to {google_target}")
            else:
                print("Google LLM already has Friday AI modifications")
        
        # Restore Cartesia TTS
        cartesia_backup = backup_dir / "cartesia_tts_modified.py"
        cartesia_target = venv_path / "Lib" / "site-packages" / "livekit" / "plugins" / "cartesia" / "tts.py"
        
        if cartesia_backup.exists() and cartesia_target.exists():
            # Check if target needs updating
            with open(cartesia_target, 'r', encoding='utf-8') as f:
                target_content = f.read()
            
            if "FRIDAY AI:" not in target_content:
                shutil.copy2(cartesia_backup, cartesia_target)
                print(f"Restored modified Cartesia TTS to {cartesia_target}")
            else:
                print("Cartesia TTS already has Friday AI modifications")
        
        return True
        
    except Exception as e:
        print(f"Error restoring plugins: {e}")
        return False

def check_and_setup_plugins():
    """Main function to check and setup plugins"""
    print("FRIDAY AI: Checking plugin setup...")
    
    # First backup any existing modifications
    backup_current_plugins()
    
    # Then try to restore from backup
    if restore_modified_plugins():
        print("FRIDAY AI: Plugin setup completed!")
        return True
    else:
        print("FRIDAY AI: Using runtime patching for conversation logging")
        return False

if __name__ == "__main__":
    check_and_setup_plugins()