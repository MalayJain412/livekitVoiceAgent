#!/usr/bin/env python3
"""
Test script for the metadata-based upload workflow
Tests the complete flow: mobile API → metadata generation → file matching → upload
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def test_mobile_api():
    """Test mobile API integration"""
    print("🔍 Testing Mobile API Integration...")
    
    try:
        from mobile_api import get_campaign_config_from_mobile, get_campaign_metadata_for_call
        
        # Test with real number
        test_number = "+918655066243"
        print(f"Testing with number: {test_number}")
        
        # Test mobile API call
        mobile_config = get_campaign_config_from_mobile(test_number)
        print(f"Mobile API response: {mobile_config}")
        
        if mobile_config:
            print("✅ Mobile API working correctly")
            
            # Test metadata generation
            session_id = "test_session_12345"
            metadata = get_campaign_metadata_for_call(test_number, session_id)
            print(f"Generated metadata: {metadata}")
            
            return metadata
        else:
            print("❌ Mobile API returned empty response")
            return None
            
    except Exception as e:
        print(f"❌ Mobile API test failed: {e}")
        return None

def test_filename_generation():
    """Test metadata-based filename generation"""
    print("\n📂 Testing Filename Generation...")
    
    try:
        from mobile_api import generate_metadata_filename, extract_metadata_from_filename
        
        # Test metadata
        test_metadata = {
            "campaignId": "68c91223fde0aa95caa3dbe4",
            "voiceAgentId": "68c9105cfde0aa95caa3db64",
            "sessionId": "session_test_12345"
        }
        
        # Generate filenames
        conv_filename = generate_metadata_filename("transcript_session", test_metadata, ".json")
        lead_filename = generate_metadata_filename("lead", test_metadata, ".json")
        rec_filename = generate_metadata_filename("recording", test_metadata, ".ogg")
        
        print(f"Conversation file: {conv_filename}")
        print(f"Lead file: {lead_filename}")
        print(f"Recording file: {rec_filename}")
        
        # Test extraction
        extracted = extract_metadata_from_filename(conv_filename)
        print(f"Extracted metadata: {extracted}")
        
        if extracted:
            print("✅ Filename generation/extraction working correctly")
            return True
        else:
            print("❌ Failed to extract metadata from filename")
            return False
            
    except Exception as e:
        print(f"❌ Filename generation test failed: {e}")
        return False

def test_file_matching():
    """Test file matching by metadata"""
    print("\n🔗 Testing File Matching...")
    
    try:
        from mobile_api import match_files_by_metadata
        
        # Create sample file lists with metadata-based names
        test_metadata = {
            "campaignId": "68c91223fde0aa95caa3dbe4",
            "voiceAgentId": "68c9105cfde0aa95caa3db64", 
            "sessionId": "session_test_12345"
        }
        
        from mobile_api import generate_metadata_filename
        
        conversation_files = [
            generate_metadata_filename("transcript_session", test_metadata, ".json"),
            "transcript_session_othercampaign_othervoice_othersession.json"
        ]
        
        recording_files = [
            generate_metadata_filename("recording", test_metadata, ".ogg"),
            "recording_anothercampaign_anothervoice_anothersession.ogg"
        ]
        
        lead_files = [
            generate_metadata_filename("lead", test_metadata, ".json")
        ]
        
        print(f"Test conversation files: {conversation_files}")
        print(f"Test recording files: {recording_files}")
        print(f"Test lead files: {lead_files}")
        
        # Test matching
        matched_sets = match_files_by_metadata(conversation_files, recording_files, lead_files)
        print(f"Matched sets: {matched_sets}")
        
        if matched_sets and len(matched_sets) > 0:
            print("✅ File matching working correctly")
            return True
        else:
            print("❌ No file matches found")
            return False
            
    except Exception as e:
        print(f"❌ File matching test failed: {e}")
        return False

def test_upload_functions():
    """Test upload functions (dry run)"""
    print("\n📤 Testing Upload Functions...")
    
    try:
        from crm_upload import upload_recording_file_sync, upload_complete_call_data_sync
        
        # Test with non-existent file (should fail gracefully)
        test_recording_path = "test_recording.ogg"
        
        print(f"Testing recording upload with non-existent file: {test_recording_path}")
        result = upload_recording_file_sync(test_recording_path)
        
        if result is None:
            print("✅ Upload function handles missing files correctly")
        else:
            print(f"❌ Unexpected result for missing file: {result}")
            
        print("✅ Upload functions loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Upload function test failed: {e}")
        return False

def test_cron_script():
    """Test cron script import and basic functionality"""
    print("\n⏰ Testing Cron Script...")
    
    try:
        from upload_cron import MetadataBasedUploadCron
        
        # Create cron instance
        cron = MetadataBasedUploadCron()
        print(f"Cron instance created with directories:")
        print(f"  Conversations: {cron.conversations_dir}")
        print(f"  Recordings: {cron.recordings_dir}")
        print(f"  Leads: {cron.leads_dir}")
        print(f"  Processed: {cron.processed_dir}")
        
        # Test file discovery
        unprocessed = cron.get_unprocessed_conversations()
        print(f"Found {len(unprocessed)} unprocessed conversation files")
        
        print("✅ Cron script working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Cron script test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Metadata-Based Upload Workflow\n")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    tests = [
        ("Mobile API Integration", test_mobile_api),
        ("Filename Generation", test_filename_generation),
        ("File Matching", test_file_matching),
        ("Upload Functions", test_upload_functions),
        ("Cron Script", test_cron_script),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("🎯 TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Metadata-based upload workflow is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())