#!/usr/bin/env python3
"""
FRIDAY AI: Apply Plugin Modifications Script for Docker Deployment
This script automatically applies the conversation logging modifications to installed LiveKit plugins.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def find_plugin_files():
    """Find the installed LiveKit plugin files in the container"""
    
    plugin_locations = {}
    
    # Try to find the site-packages directory
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import site; print(site.getsitepackages()[0])"
        ], capture_output=True, text=True, check=True)
        
        site_packages = result.stdout.strip()
        print(f"FRIDAY AI: Found site-packages at: {site_packages}")
        
        # Look for Google LLM plugin
        google_llm_path = Path(site_packages) / "livekit" / "plugins" / "google" / "llm.py"
        if google_llm_path.exists():
            plugin_locations['google_llm'] = str(google_llm_path)
            print(f"FRIDAY AI: Found Google LLM at: {google_llm_path}")
        else:
            print(f"FRIDAY AI: Warning - Google LLM not found at: {google_llm_path}")
        
        # Look for Cartesia TTS plugin
        cartesia_tts_path = Path(site_packages) / "livekit" / "plugins" / "cartesia" / "tts.py"
        if cartesia_tts_path.exists():
            plugin_locations['cartesia_tts'] = str(cartesia_tts_path)
            print(f"FRIDAY AI: Found Cartesia TTS at: {cartesia_tts_path}")
        else:
            print(f"FRIDAY AI: Warning - Cartesia TTS not found at: {cartesia_tts_path}")
            
    except subprocess.CalledProcessError as e:
        print(f"FRIDAY AI: Error finding site-packages: {e}")
        return {}
    
    return plugin_locations


def backup_original_files(plugin_locations):
    """Create backups of original plugin files"""
    
    backup_dir = Path("/app/original_plugin_backups")
    backup_dir.mkdir(exist_ok=True)
    
    for plugin_name, plugin_path in plugin_locations.items():
        try:
            backup_path = backup_dir / f"{plugin_name}_original.py"
            shutil.copy2(plugin_path, backup_path)
            print(f"FRIDAY AI: Backed up {plugin_name} to {backup_path}")
        except Exception as e:
            print(f"FRIDAY AI: Warning - Could not backup {plugin_name}: {e}")


def apply_modifications(plugin_locations):
    """Apply the conversation logging modifications"""
    
    backup_dir = Path("/app/backup_plugin_modifications")
    
    if not backup_dir.exists():
        print(f"FRIDAY AI: Error - Backup directory not found: {backup_dir}")
        return False
    
    success_count = 0
    
    # Apply Google LLM modifications
    if 'google_llm' in plugin_locations:
        try:
            google_backup = backup_dir / "google_llm_modified.py"
            if google_backup.exists():
                shutil.copy2(google_backup, plugin_locations['google_llm'])
                print(f"FRIDAY AI: Applied Google LLM modifications")
                success_count += 1
            else:
                print(f"FRIDAY AI: Error - Google LLM backup not found: {google_backup}")
        except Exception as e:
            print(f"FRIDAY AI: Error applying Google LLM modifications: {e}")
    
    # Apply Cartesia TTS modifications
    if 'cartesia_tts' in plugin_locations:
        try:
            cartesia_backup = backup_dir / "cartesia_tts_modified.py"
            if cartesia_backup.exists():
                shutil.copy2(cartesia_backup, plugin_locations['cartesia_tts'])
                print(f"FRIDAY AI: Applied Cartesia TTS modifications")
                success_count += 1
            else:
                print(f"FRIDAY AI: Error - Cartesia TTS backup not found: {cartesia_backup}")
        except Exception as e:
            print(f"FRIDAY AI: Error applying Cartesia TTS modifications: {e}")
    
    return success_count == len(plugin_locations)


def verify_modifications(plugin_locations):
    """Verify that modifications were applied correctly"""
    
    verification_passed = True
    
    for plugin_name, plugin_path in plugin_locations.items():
        try:
            with open(plugin_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for FRIDAY AI marker
            if "FRIDAY AI:" in content:
                print(f"FRIDAY AI: ✅ {plugin_name} modifications verified")
            else:
                print(f"FRIDAY AI: ❌ {plugin_name} modifications not found")
                verification_passed = False
                
            # Check for specific logging functions
            if plugin_name == 'google_llm' and "_log_user_message" in content:
                print(f"FRIDAY AI: ✅ Google LLM logging function found")
            elif plugin_name == 'cartesia_tts' and "_log_tts_message" in content:
                print(f"FRIDAY AI: ✅ Cartesia TTS logging function found")
            else:
                print(f"FRIDAY AI: ❌ {plugin_name} logging function not found")
                verification_passed = False
                
        except Exception as e:
            print(f"FRIDAY AI: Error verifying {plugin_name}: {e}")
            verification_passed = False
    
    return verification_passed


def main():
    """Main function to apply all modifications"""
    
    print("FRIDAY AI: Starting plugin modification process...")
    print("=" * 60)
    
    # Find plugin files
    plugin_locations = find_plugin_files()
    
    if not plugin_locations:
        print("FRIDAY AI: No plugin files found. This might be normal if plugins aren't installed yet.")
        return True
    
    print(f"FRIDAY AI: Found {len(plugin_locations)} plugin files to modify")
    
    # Backup original files
    print("\nFRIDAY AI: Creating backups of original files...")
    backup_original_files(plugin_locations)
    
    # Apply modifications
    print("\nFRIDAY AI: Applying conversation logging modifications...")
    if apply_modifications(plugin_locations):
        print("FRIDAY AI: ✅ All modifications applied successfully")
    else:
        print("FRIDAY AI: ❌ Some modifications failed")
        return False
    
    # Verify modifications
    print("\nFRIDAY AI: Verifying modifications...")
    if verify_modifications(plugin_locations):
        print("FRIDAY AI: ✅ All modifications verified successfully")
        print("FRIDAY AI: Plugin modification process completed!")
        return True
    else:
        print("FRIDAY AI: ❌ Verification failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
