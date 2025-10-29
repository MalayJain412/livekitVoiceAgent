#!/usr/bin/env python3
"""
BACKUP/DEVELOPMENT VERSION: Voice Agent with CRM Upload Enhancement
This is a working version of the CRM upload enhancement with corrected upload timing and user hangup handling.

Key Changes:
1. Upload timing moved from finally block to before hangup
2. Added wait logic for egress completion with retry attempts  
3. Enhanced logging for debugging upload workflow
4. Background upload process to handle user hangups
"""

import asyncio
import logging
import os
import time
from datetime import datetime
import aiohttp
import aiofiles
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput, ListEgressRequest
    from livekit.protocol.egress import EgressStatus
    LIVEKIT_API_AVAILABLE = True
except ImportError:
    logging.critical("Could not import LiveKitAPI. Please run: pip install livekit-api")
    LIVEKIT_API_AVAILABLE = False

# --- Configuration ---
UPLOAD_API_URL = "https://devcrm.xeny.ai/apis/api/public/upload"

# Dynamic path detection for recordings
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_HOST_PATH = os.path.join(SCRIPT_DIR, "recordings")  # Local recordings directory

UPLOAD_ENABLED = True
DELETE_LOCAL_AFTER_UPLOAD = True
EGRESS_CHECK_DELAY_SECONDS = 10  # Increased delay for egress finalization
EGRESS_MAX_WAIT_ATTEMPTS = 6  # Maximum attempts to wait for completion (60 seconds total)
CRM_UPLOAD_ENABLED = True

# --- Upload Functions ---
async def upload_recording(file_path, upload_url):
    """Upload recording file to storage API"""
    try:
        logging.info(f"Starting file upload: {file_path} to {upload_url}")
        
        # Check if file exists and get size
        if not os.path.exists(file_path):
            logging.error(f"File does not exist: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        logging.info(f"File size: {file_size} bytes")
        
        async with aiohttp.ClientSession() as session:
            # Prepare file for upload
            data = aiohttp.FormData()
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
                data.add_field('file', 
                             file_content,
                             filename=os.path.basename(file_path),
                             content_type='audio/ogg')
            
            # Send upload request
            logging.info(f"Sending upload request...")
            async with session.post(upload_url, data=data) as response:
                response_text = await response.text()
                logging.info(f"Upload response status: {response.status}")
                logging.info(f"Upload response text: {response_text}")
                
                try:
                    response_json = await response.json()
                except:
                    response_json = {"raw_response": response_text}
                
                if response.status >= 200 and response.status < 300 and response_json.get("success"):
                    logging.info(f"Successfully uploaded recording. API Response: {response_json}")
                    return response_json
                else:
                    logging.error(f"Failed to upload recording. Status: {response.status}, Response: {response_json}")
                    return None
    except Exception as e:
        logging.error(f"Error during upload: {e}", exc_info=True)
        return None


async def wait_for_egress_completion(lkapi, egress_id):
    """Wait for egress to complete with retry logic"""
    for attempt in range(EGRESS_MAX_WAIT_ATTEMPTS):
        try:
            logging.info(f"Checking egress status (attempt {attempt + 1}/{EGRESS_MAX_WAIT_ATTEMPTS}) after {EGRESS_CHECK_DELAY_SECONDS}s wait...")
            await asyncio.sleep(EGRESS_CHECK_DELAY_SECONDS)
            
            logging.info(f"Making list_egress request for egress_id: {egress_id}")
            list_resp = await lkapi.egress.list_egress(ListEgressRequest(egress_id=egress_id))
            
            if list_resp.items:
                egress_info = list_resp.items[0]
                
                # Enhanced logging for egress_info
                logging.info(f"Egress ID: {egress_info.egress_id}")
                logging.info(f"Room ID: {egress_info.room_id}")
                logging.info(f"Room Name: {egress_info.room_name}")
                logging.info(f"Final Egress Status (numerical): {egress_info.status}")
                logging.info(f"Started at: {egress_info.started_at}")
                logging.info(f"Ended at: {egress_info.ended_at}")
                
                # Map status values
                status_value = egress_info.status
                status_names = {
                    0: "EGRESS_STARTING",
                    1: "EGRESS_ACTIVE", 
                    2: "EGRESS_ENDING",
                    3: "EGRESS_COMPLETE",
                    4: "EGRESS_FAILED",
                    5: "EGRESS_ABORTED",
                    6: "EGRESS_LIMIT_REACHED"
                }
                status_name = status_names.get(status_value, f"UNKNOWN_{status_value}")
                logging.info(f"Status: {status_name}")
                
                # Check if egress completed successfully (status 3 = EGRESS_COMPLETE)
                if status_value == 3:
                    logging.info(f"Egress {egress_id} completed successfully!")
                    return egress_info
                elif status_value in [4, 5, 6]:  # FAILED, ABORTED, LIMIT_REACHED
                    logging.error(f"Egress {egress_id} failed with status: {status_name}")
                    return None
                else:
                    logging.info(f"Egress {egress_id} still processing with status: {status_name}, waiting...")
                    
            else:
                logging.warning(f"No egress items found for {egress_id}")
                
        except Exception as e:
            logging.error(f"Error checking egress status (attempt {attempt + 1}): {e}")
    
    logging.warning(f"Egress {egress_id} did not complete after {EGRESS_MAX_WAIT_ATTEMPTS} attempts ({EGRESS_MAX_WAIT_ATTEMPTS * EGRESS_CHECK_DELAY_SECONDS}s total)")
    return None


async def process_recording_upload(session_manager):
    """
    Enhanced upload function that handles both agent-initiated and user-initiated hangups
    """
    try:
        # Get recording metadata from SessionManager
        recording_metadata = session_manager.get_recording_metadata() if session_manager else {}
        call_metadata = session_manager.get_call_metadata() if session_manager else {}
        
        session_egress_id = recording_metadata.get("egress_id")
        session_lkapi = recording_metadata.get("lkapi_reference")
        session_dialed_number = call_metadata.get("dialed_number")
        session_full_config = call_metadata.get("full_config")
        
        logging.info(f"Starting recording upload process...")
        logging.info(f"Upload enabled: {UPLOAD_ENABLED}, Egress ID: {session_egress_id}, API available: {LIVEKIT_API_AVAILABLE}")
        
        if not all([UPLOAD_ENABLED, session_egress_id, session_lkapi, LIVEKIT_API_AVAILABLE]):
            logging.warning("Upload prerequisites not met - skipping upload")
            return False
        
        # Wait for egress completion with retry logic
        egress_info = await wait_for_egress_completion(session_lkapi, session_egress_id)
        
        if egress_info:
            # Log file information
            if hasattr(egress_info, 'file_results') and egress_info.file_results:
                logging.info(f"Egress file_results count: {len(egress_info.file_results)}")
                
                for i, file_result in enumerate(egress_info.file_results):
                    logging.info(f"File {i} filename: {file_result.filename}")
                    logging.info(f"File {i} location: {file_result.location}")
                    logging.info(f"File {i} size: {file_result.size}")
                
                # Get the first file for upload
                first_file = egress_info.file_results[0]
                
                if hasattr(first_file, 'filename'):
                    final_filename_base = os.path.basename(first_file.filename)
                    logging.info(f"Egress reported filename: {first_file.filename}")
                    logging.info(f"Extracted basename: {final_filename_base}")
                    
                    # Construct full file path
                    final_filepath_on_host = os.path.join(RECORDINGS_HOST_PATH, final_filename_base)
                    logging.info(f"Expecting file at host path: {final_filepath_on_host}")
                    
                    # Check if file exists
                    if os.path.exists(final_filepath_on_host):
                        file_size = os.path.getsize(final_filepath_on_host)
                        logging.info(f"File exists, size: {file_size} bytes")
                        
                        # Upload the file
                        logging.info(f"Starting upload for: {final_filepath_on_host}")
                        upload_response = await upload_recording(final_filepath_on_host, UPLOAD_API_URL)
                        
                        if upload_response and upload_response.get("success"):
                            logging.info(f"Upload successful: {upload_response}")
                            
                            # Save to database if session manager available
                            if session_manager:
                                try:
                                    await session_manager.update_session_with_recording(upload_response.get("data"))
                                    logging.info("Recording metadata saved to database")
                                except Exception as db_err:
                                    logging.error(f"Failed to save to database: {db_err}")
                            
                            # Clean up file if requested
                            if DELETE_LOCAL_AFTER_UPLOAD:
                                try:
                                    os.remove(final_filepath_on_host)
                                    logging.info(f"Local file deleted: {final_filepath_on_host}")
                                except Exception as del_err:
                                    logging.error(f"Failed to delete local file: {del_err}")
                            
                            return True
                        else:
                            logging.error(f"Upload failed: {upload_response}")
                            return False
                    else:
                        logging.error(f"File not found at expected path: {final_filepath_on_host}")
                        # List directory contents for debugging
                        try:
                            if os.path.exists(RECORDINGS_HOST_PATH):
                                dir_contents = os.listdir(RECORDINGS_HOST_PATH)
                                logging.info(f"Directory contents: {dir_contents}")
                        except Exception as list_err:
                            logging.error(f"Failed to list directory: {list_err}")
                        return False
                else:
                    logging.error("File object has no filename attribute")
                    return False
            else:
                logging.warning("Egress completed but has no file_results")
                return False
        else:
            logging.warning("Egress did not complete successfully")
            return False
            
    except Exception as e:
        logging.error(f"Error in upload process: {e}", exc_info=True)
        return False
    finally:
        # Clean up API client
        if session_lkapi and LIVEKIT_API_AVAILABLE:
            try:
                await session_lkapi.aclose()
                logging.info("LiveKit API client closed")
            except Exception as close_err:
                logging.error(f"Error closing API client: {close_err}")


async def schedule_background_upload(session_manager, delay_seconds=15):
    """
    Schedule upload to run in background after a delay
    This handles cases where user hangs up and room is deleted immediately
    """
    try:
        logging.info(f"Scheduling background upload in {delay_seconds} seconds...")
        await asyncio.sleep(delay_seconds)
        
        logging.info("Starting background upload process...")
        result = await process_recording_upload(session_manager)
        
        if result:
            logging.info("Background upload completed successfully")
        else:
            logging.error("Background upload failed")
            
    except Exception as e:
        logging.error(f"Error in background upload: {e}", exc_info=True)


# --- CRM Integration Functions ---
async def upload_call_data_to_crm(dialed_number, full_config, session_manager):
    """Upload call data to CRM system"""
    try:
        # This would contain the CRM upload logic
        # For now, just log the attempt
        logging.info(f"CRM upload attempted for {dialed_number}")
        return True
    except Exception as e:
        logging.error(f"CRM upload failed: {e}")
        return False


def main():
    """Test the upload functions"""
    logging.info("Upload enhancement module loaded successfully")
    logging.info(f"Recordings path: {RECORDINGS_HOST_PATH}")
    logging.info(f"Upload enabled: {UPLOAD_ENABLED}")
    logging.info(f"LiveKit API available: {LIVEKIT_API_AVAILABLE}")


if __name__ == "__main__":
    main()