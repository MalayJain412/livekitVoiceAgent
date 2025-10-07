#!/usr/bin/env python3
"""
FRIDAY AI: Verify Plugin Modifications Script for Docker Deployment
This script verifies that the conversation logging modifications were applied correctly.
"""

import os
import sys
import subprocess
from pathlib import Path


def verify_plugin_modifications():
    """Verify that plugin modifications are working correctly"""
    
    verification_results = {
        'google_llm': False,
        'cartesia_tts': False,
        'config_import': False,
        'logging_functions': False
    }
    
    try:
        # Find site-packages
        result = subprocess.run([
            sys.executable, "-c", 
            "import site; print(site.getsitepackages()[0])"
        ], capture_output=True, text=True, check=True)
        
        site_packages = Path(result.stdout.strip())
        print(f"FRIDAY AI: Checking plugins in: {site_packages}")
        
        # Check Google LLM
        google_llm_path = site_packages / "livekit" / "plugins" / "google" / "llm.py"
        if google_llm_path.exists():
            with open(google_llm_path, 'r', encoding='utf-8') as f:
                google_content = f.read()
            
            if "FRIDAY AI:" in google_content and "_log_user_message" in google_content:
                verification_results['google_llm'] = True
                print("FRIDAY AI: ✅ Google LLM modifications verified")
            else:
                print("FRIDAY AI: ❌ Google LLM modifications not found")
        else:
            print(f"FRIDAY AI: ❌ Google LLM file not found: {google_llm_path}")
        
        # Check Cartesia TTS
        cartesia_tts_path = site_packages / "livekit" / "plugins" / "cartesia" / "tts.py"
        if cartesia_tts_path.exists():
            with open(cartesia_tts_path, 'r', encoding='utf-8') as f:
                cartesia_content = f.read()
            
            if "FRIDAY AI:" in cartesia_content and "_log_tts_message" in cartesia_content:
                verification_results['cartesia_tts'] = True
                print("FRIDAY AI: ✅ Cartesia TTS modifications verified")
            else:
                print("FRIDAY AI: ❌ Cartesia TTS modifications not found")
        else:
            print(f"FRIDAY AI: ❌ Cartesia TTS file not found: {cartesia_tts_path}")
    
    except Exception as e:
        print(f"FRIDAY AI: Error during verification: {e}")
        return False
    
    # Check if config.py is accessible
    try:
        sys.path.insert(0, '/app')
        import config
        config.setup_conversation_log()
        verification_results['config_import'] = True
        print("FRIDAY AI: ✅ Config module import and setup verified")
    except Exception as e:
        print(f"FRIDAY AI: ❌ Config module verification failed: {e}")
    
    # Test logging functions
    try:
        if verification_results['google_llm'] and verification_results['cartesia_tts']:
            # Try to import and test the modified plugins
            from livekit.plugins.google.llm import LLM as GoogleLLM
            from livekit.plugins.cartesia.tts import TTS as CartesiaTTS
            
            # Check if logging methods exist
            llm = GoogleLLM()
            tts = CartesiaTTS()
            
            if hasattr(llm, '_log_user_message') and hasattr(tts, '_log_tts_message'):
                verification_results['logging_functions'] = True
                print("FRIDAY AI: ✅ Logging functions accessible")
            else:
                print("FRIDAY AI: ❌ Logging functions not accessible")
    except Exception as e:
        print(f"FRIDAY AI: ❌ Logging function test failed: {e}")
    
    return verification_results


def test_conversation_logging():
    """Test the complete conversation logging workflow"""
    
    try:
        print("\nFRIDAY AI: Testing conversation logging workflow...")
        
        # Import modified plugins
        from livekit.plugins.google.llm import LLM as GoogleLLM
        from livekit.plugins.cartesia.tts import TTS as CartesiaTTS
        
        # Test user message logging
        llm = GoogleLLM()
        test_user_input = "Test user message"
        llm._log_user_message(test_user_input, "voice")
        print("FRIDAY AI: ✅ User message logging test passed")
        
        # Test agent response logging  
        tts = CartesiaTTS()
        test_agent_response = "Test agent response"
        tts._log_tts_message(test_agent_response)
        print("FRIDAY AI: ✅ Agent response logging test passed")
        
        # Check if conversation file was created
        import config
        log_path = config.get_conversation_log_path()
        if os.path.exists(log_path):
            print(f"FRIDAY AI: ✅ Conversation log created at: {log_path}")
            return True
        else:
            print(f"FRIDAY AI: ❌ Conversation log not found at: {log_path}")
            return False
            
    except Exception as e:
        print(f"FRIDAY AI: ❌ Conversation logging test failed: {e}")
        return False


def main():
    """Main verification function"""
    
    print("FRIDAY AI: Starting plugin modification verification...")
    print("=" * 60)
    
    # Verify modifications
    verification_results = verify_plugin_modifications()
    
    # Count successful verifications
    success_count = sum(verification_results.values())
    total_checks = len(verification_results)
    
    print(f"\nFRIDAY AI: Verification Results: {success_count}/{total_checks} checks passed")
    
    # Detailed results
    for check, passed in verification_results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    # Test conversation logging if basic verifications passed
    if verification_results['google_llm'] and verification_results['cartesia_tts']:
        logging_test_passed = test_conversation_logging()
    else:
        logging_test_passed = False
        print("\nFRIDAY AI: Skipping logging test due to failed basic verifications")
    
    # Overall result
    overall_success = success_count == total_checks and logging_test_passed
    
    if overall_success:
        print("\nFRIDAY AI: ✅ All verifications passed! Plugin modifications are working correctly.")
    else:
        print("\nFRIDAY AI: ❌ Some verifications failed. Please check the plugin modifications.")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
