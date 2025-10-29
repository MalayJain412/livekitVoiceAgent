#!/usr/bin/env python3
"""
Test the integrated CRM upload workflow
"""
import asyncio
import json
import os
from datetime import datetime
from crm_upload import upload_call_data_from_conversation

async def test_integrated_crm():
    print("=" * 60)
    print("TESTING INTEGRATED CRM UPLOAD WORKFLOW")
    print("=" * 60)
    
    # Load a recent conversation file
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        print("❌ Conversations directory not found")
        return False
    
    # Find the most recent MongoDB-format conversation file
    conv_files = []
    for file in os.listdir(conversations_dir):
        if file.startswith("transcript_session_") and file.endswith(".json"):
            file_path = os.path.join(conversations_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Verify it's MongoDB format
                if isinstance(data, dict) and 'session_id' in data and 'items' in data:
                    conv_files.append((file_path, os.path.getmtime(file_path)))
            except:
                continue
    
    if not conv_files:
        print("❌ No MongoDB-format conversation files found")
        return False
    
    # Sort by modification time (newest first)
    conv_files.sort(key=lambda x: x[1], reverse=True)
    latest_conv_file = conv_files[0][0]
    
    print(f"📄 Using conversation file: {os.path.basename(latest_conv_file)}")
    
    # Load conversation data
    with open(latest_conv_file, 'r', encoding='utf-8') as f:
        conversation_data = json.load(f)
    
    print(f"📊 Conversation has {len(conversation_data.get('items', []))} items")
    print(f"⏱️  Duration: {conversation_data.get('duration_seconds')} seconds")
    print(f"🆔 Session ID: {conversation_data.get('session_id')}")
    
    # Test CRM configuration (Urban Piper campaign)
    campaign_id = "68c91223fde0aa95caa3dbe4"
    voice_agent_id = "68c9105cfde0aa95caa3db64"
    client_id = "68c90d626052ee95ac77059d"
    caller_phone = "+919876543210"
    
    # Generate call ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = conversation_data.get('session_id', 'unknown')
    call_id = f"CALL-{timestamp}-{session_id[-8:] if session_id else 'test'}"
    
    print(f"🎯 Call ID: {call_id}")
    print(f"📞 Caller: {caller_phone}")
    
    # Test the integrated upload function
    print("\n🚀 Testing CRM upload...")
    
    try:
        success = await upload_call_data_from_conversation(
            campaign_id=campaign_id,
            voice_agent_id=voice_agent_id,
            client_id=client_id,
            call_id=call_id,
            caller_phone=caller_phone,
            conversation_data=conversation_data,
            recording_url="https://devcrm.xeny.ai/apis/uploads/recordings/1761646722349.ogg",
            recording_size=2048000,  # 2MB test size
            direction="inbound",
            status="completed"
        )
        
        if success:
            print("✅ CRM upload successful!")
            print(f"📈 Call data uploaded for {call_id}")
        else:
            print("❌ CRM upload failed")
            
        return success
        
    except Exception as e:
        print(f"❌ Error during CRM upload: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_integrated_crm()
    
    print("\n" + "=" * 60)
    print(f"INTEGRATION TEST: {'✅ PASSED' if success else '❌ FAILED'}")
    print("=" * 60)
    
    if success:
        print("\n🎉 The integrated CRM upload workflow is working!")
        print("📋 Next steps:")
        print("  1. Recordings will be uploaded to CRM storage")
        print("  2. Conversation transcripts will be processed")
        print("  3. Lead data will be extracted and stored")
        print("  4. Call analytics will be generated")
    else:
        print("\n🔧 Check the logs for debugging information")

if __name__ == "__main__":
    asyncio.run(main())