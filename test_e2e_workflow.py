#!/usr/bin/env python3
"""
End-to-End Workflow Test
Tests the complete flow: Audio → Recording → Conversation → CRM Upload
With comprehensive logging for debugging
"""
import asyncio
import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import aiofiles

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WorkflowTest')

class WorkflowTester:
    def __init__(self):
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.generate_session_suffix()}"
        self.call_id = f"CALL-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{self.session_id[-8:]}"
        self.start_time = datetime.utcnow()
        self.conversation_file = None
        self.recording_file = None
        
        logger.info(f"🚀 Starting workflow test - Session: {self.session_id}")
        logger.info(f"🎯 Call ID: {self.call_id}")
    
    def generate_session_suffix(self):
        """Generate a random session suffix"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    async def step1_simulate_audio_recording(self):
        """Step 1: Simulate audio file creation and recording upload"""
        logger.info("=" * 60)
        logger.info("STEP 1: SIMULATE AUDIO RECORDING")
        logger.info("=" * 60)
        
        try:
            # Create a mock recording file
            recordings_dir = Path("recordings")
            recordings_dir.mkdir(exist_ok=True)
            
            mock_filename = f"{self.session_id}_recording.ogg"
            self.recording_file = recordings_dir / mock_filename
            
            # Create a mock audio file (small binary content)
            mock_audio_content = b"OGG_MOCK_AUDIO_DATA" * 1000  # ~19KB mock file
            
            async with aiofiles.open(self.recording_file, 'wb') as f:
                await f.write(mock_audio_content)
            
            logger.info(f"✅ Mock recording created: {self.recording_file}")
            logger.info(f"📊 File size: {len(mock_audio_content)} bytes")
            
            # Test recording upload
            upload_url = "https://devcrm.xeny.ai/apis/api/public/upload"
            logger.info(f"🚀 Uploading recording to: {upload_url}")
            
            async with aiohttp.ClientSession() as session:
                async with aiofiles.open(self.recording_file, mode='rb') as f:
                    file_content = await f.read()

                data = aiohttp.FormData()
                data.add_field('file',
                               file_content,
                               filename=mock_filename,
                               content_type='audio/ogg')

                async with session.post(upload_url, data=data) as response:
                    response_text = await response.text()
                    
                    if response.status >= 200 and response.status < 300:
                        try:
                            response_json = await response.json(content_type=None)
                            logger.info(f"✅ Recording upload successful: {response.status}")
                            logger.debug(f"📄 Upload response: {response_json}")
                            
                            if response_json.get("success") and response_json.get("data"):
                                recording_url = response_json["data"].get("url")
                                recording_size = response_json["data"].get("size")
                                logger.info(f"🔗 Recording URL: {recording_url}")
                                logger.info(f"📊 Recording size: {recording_size} bytes")
                                return recording_url, recording_size
                            else:
                                logger.error(f"❌ Upload response missing data: {response_json}")
                                return None, None
                        except Exception as e:
                            logger.error(f"❌ Failed to parse upload response: {e}")
                            logger.error(f"📄 Raw response: {response_text}")
                            return None, None
                    else:
                        logger.error(f"❌ Recording upload failed: {response.status}")
                        logger.error(f"📄 Error response: {response_text}")
                        return None, None
                        
        except Exception as e:
            logger.error(f"❌ Error in audio recording step: {e}", exc_info=True)
            return None, None
    
    async def step2_create_conversation_file(self):
        """Step 2: Create a realistic conversation file"""
        logger.info("=" * 60)
        logger.info("STEP 2: CREATE CONVERSATION FILE")
        logger.info("=" * 60)
        
        try:
            # Create conversations directory
            conversations_dir = Path("conversations")
            conversations_dir.mkdir(exist_ok=True)
            
            # Create realistic conversation data
            end_time = self.start_time + timedelta(seconds=25)  # 25 second call
            
            conversation_data = {
                "session_id": self.session_id,
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S.%f+00:00"),
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S.%f+00:00"),
                "duration_seconds": 25.5,
                "lead_generated": False,
                "metadata": {
                    "auto_saved": True,
                    "language": "hi-IN",
                    "channel": "voice",
                    "source": "friday-ai-assistant"
                },
                "items": [
                    {
                        "_id": f"test_id_1_{int(time.time())}",
                        "type": "persona_applied",
                        "persona_name": "Malay Jain",
                        "has_config": True,
                        "has_session_instructions": True,
                        "has_closing": True,
                        "timestamp": self.start_time.isoformat() + "Z",
                        "session_id": self.session_id,
                        "created_at": self.start_time.strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_2_{int(time.time())}",
                        "role": "user",
                        "content": "Namaste, main Urban Piper ke baare mein jaanna chahta hun",
                        "timestamp": (self.start_time + timedelta(seconds=2)).isoformat() + "Z",
                        "source": "transcription_node",
                        "transcript_confidence": 0.95,
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_3_{int(time.time())}",
                        "role": "assistant",
                        "content": "Namaste! Main Friday hun, Malay Jain ki AI assistant. Urban Piper ke baare mein main aapko bilkul sahi jaankaari de sakti hun. Urban Piper ek leading cloud-based restaurant management platform hai jo restaurants ko online orders manage karne mein madad karta hai.",
                        "timestamp": (self.start_time + timedelta(seconds=5)).isoformat() + "Z",
                        "source": "agent_response",
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_4_{int(time.time())}",
                        "role": "user",
                        "content": "Kya aap mujhe iske features bata sakte hain?",
                        "timestamp": (self.start_time + timedelta(seconds=10)).isoformat() + "Z",
                        "source": "transcription_node",
                        "transcript_confidence": 0.92,
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=10)).strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_5_{int(time.time())}",
                        "role": "assistant",
                        "content": "Bilkul! Urban Piper ke main features hain: Multi-channel order management, Real-time inventory tracking, Customer analytics, Delivery management, aur POS integration. Kya aap kisi specific feature ke baare mein detail mein jaanna chahenge?",
                        "timestamp": (self.start_time + timedelta(seconds=15)).isoformat() + "Z",
                        "source": "agent_response",
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=15)).strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_6_{int(time.time())}",
                        "role": "user",
                        "content": "Pricing ke baare mein bataiye",
                        "timestamp": (self.start_time + timedelta(seconds=20)).isoformat() + "Z",
                        "source": "transcription_node",
                        "transcript_confidence": 0.88,
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=20)).strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "_id": f"test_id_7_{int(time.time())}",
                        "role": "assistant",
                        "content": "Urban Piper ki pricing restaurant size aur requirements ke according vary karti hai. Basic plan 5000 rupees monthly se start hota hai. Detailed pricing aur demo ke liye main aapka contact collect kar sakti hun. Kya aap interested hain?",
                        "timestamp": (self.start_time + timedelta(seconds=23)).isoformat() + "Z",
                        "source": "agent_response",
                        "session_id": self.session_id,
                        "created_at": (self.start_time + timedelta(seconds=23)).strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]
            }
            
            # Save conversation file
            conversation_filename = f"transcript_session_{self.start_time.strftime('%Y-%m-%dT%H-%M-%S.%f')}.json"
            self.conversation_file = conversations_dir / conversation_filename
            
            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Conversation file created: {self.conversation_file}")
            logger.info(f"📊 Conversation items: {len(conversation_data['items'])}")
            logger.info(f"⏱️  Duration: {conversation_data['duration_seconds']} seconds")
            logger.debug(f"📋 Sample conversation: {conversation_data['items'][1]['content'][:50]}...")
            
            return conversation_data
            
        except Exception as e:
            logger.error(f"❌ Error creating conversation file: {e}", exc_info=True)
            return None
    
    async def step3_test_crm_upload(self, recording_url, recording_size, conversation_data):
        """Step 3: Test CRM upload with the conversation data"""
        logger.info("=" * 60)
        logger.info("STEP 3: TEST CRM UPLOAD")
        logger.info("=" * 60)
        
        try:
            from crm_upload import upload_call_data_from_conversation
            
            # Campaign configuration
            campaign_id = "68c91223fde0aa95caa3dbe4"
            voice_agent_id = "68c9105cfde0aa95caa3db64"
            client_id = "68c90d626052ee95ac77059d"
            caller_phone = "+919876543210"
            
            logger.info(f"🎯 Campaign ID: {campaign_id}")
            logger.info(f"🤖 Voice Agent ID: {voice_agent_id}")
            logger.info(f"👤 Client ID: {client_id}")
            logger.info(f"📞 Caller: {caller_phone}")
            logger.info(f"🔗 Recording URL: {recording_url}")
            logger.info(f"📊 Recording Size: {recording_size}")
            
            # Test CRM upload
            logger.info("🚀 Starting CRM upload...")
            
            success = await upload_call_data_from_conversation(
                campaign_id=campaign_id,
                voice_agent_id=voice_agent_id,
                client_id=client_id,
                call_id=self.call_id,
                caller_phone=caller_phone,
                conversation_data=conversation_data,
                recording_url=recording_url,
                recording_size=recording_size,
                direction="inbound",
                status="completed"
            )
            
            if success:
                logger.info("✅ CRM upload successful!")
                logger.info(f"📈 Call data uploaded for {self.call_id}")
                return True
            else:
                logger.error("❌ CRM upload failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in CRM upload: {e}", exc_info=True)
            return False
    
    async def step4_verify_integration(self):
        """Step 4: Verify the complete integration"""
        logger.info("=" * 60)
        logger.info("STEP 4: VERIFY INTEGRATION")
        logger.info("=" * 60)
        
        try:
            # Check if files were created
            files_created = []
            
            if self.recording_file and self.recording_file.exists():
                files_created.append(f"Recording: {self.recording_file}")
                logger.info(f"✅ Recording file exists: {self.recording_file}")
            else:
                logger.warning(f"⚠️  Recording file missing: {self.recording_file}")
            
            if self.conversation_file and self.conversation_file.exists():
                files_created.append(f"Conversation: {self.conversation_file}")
                logger.info(f"✅ Conversation file exists: {self.conversation_file}")
            else:
                logger.warning(f"⚠️  Conversation file missing: {self.conversation_file}")
            
            # Log file verification
            log_file = Path("workflow_test.log")
            if log_file.exists():
                files_created.append(f"Log: {log_file}")
                logger.info(f"✅ Log file created: {log_file}")
                
                # Check log file size
                log_size = log_file.stat().st_size
                logger.info(f"📊 Log file size: {log_size} bytes")
            
            logger.info(f"📁 Files created during test: {len(files_created)}")
            for file_info in files_created:
                logger.info(f"   - {file_info}")
                
            return len(files_created) >= 2  # At least conversation and log should exist
            
        except Exception as e:
            logger.error(f"❌ Error in verification: {e}", exc_info=True)
            return False
    
    async def cleanup(self):
        """Clean up test files"""
        logger.info("=" * 60)
        logger.info("CLEANUP")
        logger.info("=" * 60)
        
        try:
            if self.recording_file and self.recording_file.exists():
                self.recording_file.unlink()
                logger.info(f"🗑️  Removed recording file: {self.recording_file}")
            
            # Keep conversation file for inspection
            if self.conversation_file and self.conversation_file.exists():
                logger.info(f"📁 Keeping conversation file for inspection: {self.conversation_file}")
            
            # Keep log file for debugging
            logger.info("📁 Keeping log file for debugging: workflow_test.log")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    async def run_complete_test(self):
        """Run the complete end-to-end test"""
        logger.info("🚀" * 20)
        logger.info("STARTING END-TO-END WORKFLOW TEST")
        logger.info("🚀" * 20)
        
        start_time = time.time()
        success = False
        
        try:
            # Step 1: Recording upload
            recording_url, recording_size = await self.step1_simulate_audio_recording()
            if not recording_url:
                logger.error("❌ Step 1 failed - Recording upload unsuccessful")
                return False
            
            # Step 2: Conversation file creation
            conversation_data = await self.step2_create_conversation_file()
            if not conversation_data:
                logger.error("❌ Step 2 failed - Conversation file creation unsuccessful")
                return False
            
            # Step 3: CRM upload
            crm_success = await self.step3_test_crm_upload(recording_url, recording_size, conversation_data)
            if not crm_success:
                logger.error("❌ Step 3 failed - CRM upload unsuccessful")
                return False
            
            # Step 4: Verification
            verification_success = await self.step4_verify_integration()
            if not verification_success:
                logger.error("❌ Step 4 failed - Integration verification unsuccessful")
                return False
            
            success = True
            
        except Exception as e:
            logger.error(f"❌ Critical error in workflow test: {e}", exc_info=True)
            success = False
        
        finally:
            await self.cleanup()
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info("🏁" * 20)
            logger.info(f"WORKFLOW TEST {'✅ COMPLETED SUCCESSFULLY' if success else '❌ FAILED'}")
            logger.info(f"⏱️  Total duration: {duration:.2f} seconds")
            logger.info(f"🆔 Session ID: {self.session_id}")
            logger.info(f"🎯 Call ID: {self.call_id}")
            logger.info("🏁" * 20)
            
            return success

async def main():
    """Main test function"""
    tester = WorkflowTester()
    success = await tester.run_complete_test()
    
    print(f"\n{'🎉 SUCCESS' if success else '💥 FAILED'}: End-to-End workflow test")
    print(f"📋 Check workflow_test.log for detailed debugging information")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())