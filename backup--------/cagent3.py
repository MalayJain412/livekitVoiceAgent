import os
from dotenv import load_dotenv
import logging
from logging_config import configure_logging
import asyncio
from typing import Optional, Tuple
import re
import time
import aiohttp  # For async HTTP requests
import aiofiles  # For async file operations
from datetime import datetime, timedelta
load_dotenv()  # Load environment variables early

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions, JobContext
from livekit.plugins import google, cartesia, deepgram, noise_cancellation, silero
from prompts import set_agent_instruction
from persona_handler import load_persona_from_dialed_number as load_persona_from_api
from tools import (
    create_lead, 
    detect_lead_intent, 
    HangupTool
)
import config
from instances import get_instances_from_payload
from session_manager import SessionManager
from validation import validate_agent_availability, hangup_call
from crm_upload import upload_call_data_from_session

try:
    from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput, ListEgressRequest
except ImportError:
    logging.critical("Could not import LiveKitAPI. Please run: pip install livekit-api")
# --- END OF CORRECTED IMPORTS ---

# Centralized logging config
try:
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

# --- Configuration (To be moved to config.py later) ---
UPLOAD_API_URL = "https://devcrm.xeny.ai/apis/api/public/upload"
RECORDINGS_HOST_PATH = "/mnt/recordings"  # CRITICAL: Must match Docker volume mapping
UPLOAD_ENABLED = True  # Basic toggle (to be improved)
DELETE_LOCAL_AFTER_UPLOAD = True  # Basic toggle (to be improved)
EGRESS_CHECK_DELAY_SECONDS = 5  # Initial delay before checking Egress status
CRM_UPLOAD_ENABLED = True  # Enable CRM call-data upload


# --- NEW FUNCTION: Upload Recording ---
async def upload_recording(filepath: str, api_url: str):
    """Uploads the recording file to the specified API."""
    if not os.path.exists(filepath):
        logging.error(f"Upload failed: File not found at {filepath}")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(filepath, mode='rb') as f:
                file_content = await f.read()

            data = aiohttp.FormData()
            # Ensure field name 'file' matches API expectation
            data.add_field('file',
                           file_content,
                           filename=os.path.basename(filepath),
                           content_type='audio/ogg')  # Confirmed .ogg format

            logging.info(f"Uploading {os.path.basename(filepath)} ({len(file_content)} bytes) to {api_url}...")
            async with session.post(api_url, data=data) as response:
                response_text = await response.text()  # Read text first for better error logging
                try:
                    response_json = await response.json(content_type=None)  # Use content_type=None for flexibility
                except Exception:
                    logging.error(f"Failed to parse JSON response: {response_text}")
                    response_json = {"raw_response": response_text}  # Store raw text if JSON fails

                if response.status >= 200 and response.status < 300 and response_json.get("success"):
                    logging.info(f"Successfully uploaded recording. API Response: {response_json}")
                    return response_json
                else:
                    logging.error(f"Failed to upload recording. Status: {response.status}, Response: {response_json}")
                    return None
    except aiohttp.ClientError as e:
        logging.error(f"HTTP client error during upload: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during upload: {e}")
        return None


# --- NEW FUNCTION: Clean up local file ---
async def delete_local_file(filepath: str):
    """Deletes the local recording file."""
    try:
        if os.path.exists(filepath):
            # Use async remove for consistency, though sync os.remove is often fine here
            await aiofiles.os.remove(filepath)
            logging.info(f"Deleted local recording file: {filepath}")
        else:
            logging.warning(f"Attempted to delete non-existent file: {filepath}")
    except Exception as e:
        logging.error(f"Failed to delete local file {filepath}: {e}")


# --------------------------------------------
# STRICT MODE: Extract number only from room name
# --------------------------------------------
def extract_number_from_room_name(room_name: str) -> Optional[str]:
    """Extracts the dialed number from room name like 'number-_918655048643'."""
    match = re.search(r'number-[_+]?(\d+)', room_name)
    if match:
        return '+' + match.group(1)
    return None


async def get_sip_participant_and_number(ctx: JobContext) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract SIP participant and dialed number strictly from room name.
    No metadata, no fallbacks, no defaults.
    """
    try:
        room_name = ctx.room.name
        logging.info(f"Extracting dialed number from room name: {room_name}")

        dialed_number = extract_number_from_room_name(room_name)
        if not dialed_number:
            logging.warning(f"Could not extract dialed number from room name: {room_name}")
            return None, None

        logging.info(f"Successfully extracted dialed number from room name: {dialed_number}")

        # Find SIP participant identity (if exists)
        participant_identity = None
        if hasattr(ctx.room, "participants") and ctx.room.participants:
            for p in ctx.room.participants.values():
                if p.identity.startswith("sip_"):
                    participant_identity = p.identity
                    break

        return participant_identity, dialed_number

    except Exception as e:
        logging.error(f"Error extracting number from room name: {e}")
        return None, None

async def load_persona_from_dialed_number(dialed_number: str):
    """Load persona configuration from CRM API using dialed number."""
    return await load_persona_from_api(dialed_number)

def apply_persona_to_agent(agent: Agent, persona_config: dict):
    """Apply persona configuration to the agent."""
    # This function can be used if needed to modify agent after creation
    pass

def attach_persona_to_session(session: AgentSession, full_config: dict, persona_name: str, session_instructions: str, closing_message: str):
    """Attach persona configuration to the session for later use."""
    session.persona_config = full_config
    session.persona_name = persona_name
    session.session_instructions = session_instructions
    session.closing_message = closing_message

class Assistant(Agent):
    def __init__(self, custom_instructions=None, end_call_tool=None):
        # Require custom_instructions from API - no fallback to defaults
        if not custom_instructions:
            raise ValueError("Agent requires custom_instructions from API - no default fallbacks allowed")

        super().__init__(
            instructions=custom_instructions,
            tools=[
                # get_weather, 
                # search_web, 
                # triotech_info, 
                create_lead, 
                detect_lead_intent, 
                end_call_tool],
        )


async def upload_call_data_to_crm(
    recording_url: str,
    recording_size: int,
    dialed_number: str,
    full_config: dict,
    session_manager=None
):
    """
    Upload complete call data (recording, transcript, leads) to CRM API
    
    Args:
        recording_url: URL of the uploaded recording
        recording_size: Size of recording file in bytes
        dialed_number: Phone number that was dialed
        full_config: Full persona configuration from API
        session_manager: SessionManager instance for accessing session data
    """
    try:
        # Extract campaign details from persona config
        campaigns = full_config.get("campaigns", [])
        if not campaigns:
            logging.warning("No campaigns found in persona config - skipping CRM upload")
            return False
            
        campaign = campaigns[0]
        campaign_id = campaign.get("_id")
        
        voice_agents = campaign.get("voiceAgents", [])
        if not voice_agents:
            logging.warning("No voice agents found in campaign - skipping CRM upload")
            return False
            
        voice_agent = voice_agents[0]
        voice_agent_id = voice_agent.get("_id")
        
        # Get client ID from campaign
        client_id = campaign.get("client")
        
        if not all([campaign_id, voice_agent_id, client_id]):
            logging.warning(f"Missing required IDs for CRM upload: campaign_id={campaign_id}, voice_agent_id={voice_agent_id}, client_id={client_id}")
            return False
        
        # Generate call ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        call_id = f"CALL-{timestamp}-{dialed_number.replace('+', '')[-8:]}"
        
        # Get transcript data from session manager
        transcript_data = None
        lead_data = None
        if session_manager:
            try:
                # Extract session history as transcript data
                session_history = getattr(session_manager.session, "history", None)
                if session_history:
                    # Convert session history to transcript format
                    transcript_data = await convert_session_to_transcript(session_history)
                
                # Check if any leads were created (this would need to be tracked in session)
                lead_data = getattr(session_manager.session, "generated_lead", None)
                
            except Exception as e:
                logging.warning(f"Could not extract transcript/lead data from session: {e}")
        
        # Calculate recording duration (estimate from file size if not available)
        # Rough estimate: 1 minute of OGG audio ˜ 50-100KB
        estimated_duration = max(1, recording_size // 70000)  # Conservative estimate
        
        logging.info(f"Uploading call data to CRM - Call ID: {call_id}")
        
        success = await asyncio.to_thread(
            upload_call_data_from_session,
            campaign_id=campaign_id,
            voice_agent_id=voice_agent_id,
            client_id=client_id,
            call_id=call_id,
            caller_phone=dialed_number,
            direction="inbound",
            start_time=datetime.now() - timedelta(seconds=estimated_duration + 60),  # Estimate start time
            end_time=datetime.now(),
            status="completed",
            transcript_data=transcript_data,
            lead_data=lead_data,
            recording_url=recording_url,
            recording_duration=estimated_duration,
            recording_size=recording_size
        )
        
        if success:
            logging.info(f"Successfully uploaded call data to CRM for call {call_id}")
        else:
            logging.error(f"Failed to upload call data to CRM for call {call_id}")
            
        return success
        
    except Exception as e:
        logging.error(f"Error uploading call data to CRM: {e}", exc_info=True)
        return False


async def convert_session_to_transcript(session_history):
    """
    Convert LiveKit session history to transcript format for CRM API
    
    Args:
        session_history: LiveKit session history object
        
    Returns:
        Dict: Formatted transcript data for CRM API
    """
    try:
        # Try to get items from session history
        items = []
        if hasattr(session_history, "items"):
            items = getattr(session_history, "items", [])
        elif hasattr(session_history, "to_dict"):
            history_dict = session_history.to_dict()
            items = history_dict.get("items", [])
        elif hasattr(session_history, "toJSON"):
            import json
            history_json = session_history.toJSON()
            history_dict = json.loads(history_json) if isinstance(history_json, str) else history_json
            items = history_dict.get("items", [])
        
        # Convert items to CRM format
        conversation_items = []
        start_time = None
        end_time = None
        
        for item in items:
            if isinstance(item, dict):
                role = item.get("role", "")
                content = item.get("content", "")
                
                # Skip system messages and empty content
                if role in ["user", "assistant"] and content:
                    conversation_item = {
                        "role": role,
                        "content": str(content),
                        "timestamp": datetime.now().isoformat() + "Z",  # Current time as fallback
                        "source": "livekit-session"
                    }
                    conversation_items.append(conversation_item)
                    
                    # Track timing
                    if not start_time:
                        start_time = datetime.now().isoformat() + "Z"
                    end_time = datetime.now().isoformat() + "Z"
        
        # Create transcript data structure
        transcript_data = {
            "session_id": f"livekit-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "start_time": start_time or datetime.now().isoformat() + "Z",
            "end_time": end_time or datetime.now().isoformat() + "Z",
            "duration_seconds": len(conversation_items) * 10,  # Rough estimate
            "total_items": len(conversation_items),
            "conversation_items": conversation_items,
            "lead_generated": False,  # Would need to be determined from actual lead creation
            "metadata": {
                "language": "hi-IN",  # Hindi-English mix
                "channel": "voice",
                "source": "friday-ai-assistant"
            }
        }
        
        return transcript_data
        
    except Exception as e:
        logging.error(f"Error converting session to transcript: {e}")
        return None


async def entrypoint(ctx: JobContext):
    # Setup conversation logging
    config.setup_conversation_log()
    
    # -----------------------------------------------------------------
    # --- CORRECTED RECORDING BLOCK ---
    # -----------------------------------------------------------------
    lkapi = None  # Define lkapi outside try block for cleanup
    try:
        logging.info(f"Attempting to start recording for room: {ctx.room.name}")
        
        # Environment variables are already loaded from the top of the script
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        # --- NEW DEBUG LOGGING ---
        # Log the values to confirm they are loaded correctly inside the entrypoint
        logging.info(f"Recording: URL={livekit_url}, KEY={livekit_api_key}")
        if livekit_api_secret:
            # Mask the secret for security, just show the first and last 4 chars
            logging.info(f"Recording: SECRET={livekit_api_secret[:4]}...{livekit_api_secret[-4:]}")
        else:
            logging.info("Recording: SECRET=None")
        # --- END DEBUG LOGGING ---

        if not all([livekit_url, livekit_api_key, livekit_api_secret]):
            logging.error("Cannot start recording: LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET not set.")
        else:
            # The API client needs an HTTP/S host, not WS/S
            http_host = livekit_url.replace("ws://", "http://").replace("wss://", "https://")

            # --- NEW DEBUG LOGGING ---
            logging.info(f"Recording: Initializing LiveKitAPI with host: {http_host}")
            # --- END DEBUG LOGGING ---

            # 1. Create the main API client
            lkapi = LiveKitAPI(http_host, livekit_api_key, livekit_api_secret)

            # 2. Use a unique filename with an AUDIO extension
            filename = f"recordings/{ctx.room.name}-{int(time.time())}"

            # 3. Create the file output request
            file_output = EncodedFileOutput(
                filepath=filename
                # No azure block is needed; it uses your egress.yaml config
            )

            # 4. Create the main egress request
            request = RoomCompositeEgressRequest(
                room_name=ctx.room.name,
                audio_only=True,  # This creates the combined audio file
                file_outputs=[file_output]
            )

            # 5. Start the recording
            info = await lkapi.egress.start_room_composite_egress(request)
            logging.info(f"Successfully started recording. Egress ID: {info.egress_id}, File: {filename}")

    except Exception as e:
        logging.error(f"Failed to start recording for room {ctx.room.name}: {e}")
        # Log the error but continue the call. Recording is not a critical failure.
    finally:
        # 6. Clean up the client
        if lkapi:
            await lkapi.aclose() # Use aclose() for async
    # -----------------------------------------------------------------
    # --- END OF RECORDING BLOCK ---
    # -----------------------------------------------------------------
    egress_id = info.egress_id if 'info' in locals() else None
    # --- Main Agent Logic ---
    try:
        # Extract dialed number from SIP participant in the room
        participant_identity, dialed_number = await get_sip_participant_and_number(ctx)
        
        if not dialed_number:
            logging.error("Critical: Could not extract dialed number. Aborting call setup.")
            # Create minimal session for error message
            instances = get_instances_from_payload(None)
            session = AgentSession(
                stt=instances["stt"],
                llm=instances["llm"], 
                tts=instances["tts"],
                vad=instances["vad"],
            )
            dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
            
            await session.start(
                room=ctx.room,
                agent=dummy_agent,
                room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
                room_output_options=RoomOutputOptions(audio_enabled=True),
            )
            
            await session.say("Sorry, we could not identify your call. Please try again.")
            await hangup_call()
            return
        
        logging.info(f"Extracted dialed number: {dialed_number}")
        
        # Load persona configuration from dialed number
        try:
            agent_instructions, session_instructions, closing_message, persona_name, full_config = await load_persona_from_dialed_number(dialed_number)
            logging.info(f"Successfully loaded persona for dialed number {dialed_number}: {persona_name}")
        except ValueError as e:
            logging.warning(f"Persona validation failed for {dialed_number}: {e}")
            # Create minimal session for error message
            instances = get_instances_from_payload(None)
            session = AgentSession(
                stt=instances["stt"],
                llm=instances["llm"], 
                tts=instances["tts"],
                vad=instances["vad"],
            )
            dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
            
            await session.start(
                room=ctx.room,
                agent=dummy_agent,
                room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
                room_output_options=RoomOutputOptions(audio_enabled=True),
            )
            
            await session.say("Sorry, this number is not configured for service. Please contact support.")
            await hangup_call()
            return
        except Exception as e:
            logging.error(f"Error loading persona for {dialed_number}: {e}")
            # Create minimal session for error message
            instances = get_instances_from_payload(None)
            session = AgentSession(
                stt=instances["stt"],
                llm=instances["llm"], 
                tts=instances["tts"],
                vad=instances["vad"],
            )
            dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
            
            await session.start(
                room=ctx.room,
                agent=dummy_agent,
                room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
                room_output_options=RoomOutputOptions(audio_enabled=True),
            )
            
            await session.say("Sorry, there was an error loading the service configuration. Please try again later.")
            await hangup_call()
            return
        
        # VALIDATION: Check agent availability
        is_available, failure_reason = validate_agent_availability(full_config)
        if not is_available:
            logging.warning(f"Agent validation failed: {failure_reason}")
            
            # Create minimal session for apology message
            instances = get_instances_from_payload(None)
            session = AgentSession(
                stt=instances["stt"],
                llm=instances["llm"], 
                tts=instances["tts"],
                vad=instances["vad"],
            )
            
            dummy_agent = Assistant(custom_instructions="You are a helpful assistant. Keep responses brief and polite.")
            
            await session.start(
                room=ctx.room,
                agent=dummy_agent,
                room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
                room_output_options=RoomOutputOptions(audio_enabled=True),
            )
            
            await session.say("Sorry, currently the agent is not available. Please try later.")
            await hangup_call()
            return
        
        # Create the hangup event and tool
        hangup_event = asyncio.Event()
        hangup_tool = HangupTool(hangup_event=hangup_event)

        # Create agent with persona instructions
        agent = Assistant(custom_instructions=agent_instructions, end_call_tool=hangup_tool.end_call)
        logging.info(f"Created agent with persona instructions for: {persona_name}")

        # Get AI service instances
        instances = get_instances_from_payload(full_config)
        
        session = AgentSession(
            stt=instances["stt"],
            llm=instances["llm"],
            tts=instances["tts"],
            vad=instances["vad"],
        )

        # Attach persona configuration to session
        attach_persona_to_session(session, full_config, persona_name, session_instructions, closing_message)
        
        # Initialize session manager
        session_manager = SessionManager(session)
        logging.info("SessionManager created successfully")
        
        # Setup session logging and monitoring
        await session_manager.setup_session_logging()
        await session_manager.setup_shutdown_callback()
        logging.info("SessionManager setup completed")

        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(audio_enabled=True, close_on_disconnect=False),
            room_output_options=RoomOutputOptions(audio_enabled=True),
        )

        # Log persona application event
        session_manager.log_persona_applied_event(persona_name, full_config, session_instructions, closing_message)
        
        # Start background history watcher AFTER session starts
        await session_manager.start_history_watcher()
        logging.info("SessionManager history watcher started")

        # Generate initial reply with persona-aware instructions
        if not session_instructions:
            raise ValueError(f"Session instructions required from API for persona {persona_name} - no defaults allowed")

        # Use persona's conversation structure for session behavior
        initial_instruction = session_instructions
        logging.info(f"Using persona session instructions for: {persona_name}")
        
        logging.info("Agent is running, waiting for user input or hangup signal...")
        
        # Generate the initial reply to start the conversation
        await session.generate_reply(instructions=initial_instruction)
        
        # Wait for the hangup signal
        await hangup_event.wait()
        
        logging.info("Hangup signal received.")

        # --- HANGUP SEQUENCE ---
        # Play the pre-defined closing message from the persona config
        if closing_message:
            logging.info(f"Playing closing message: {closing_message}")
            await session.say(closing_message)
            # Add a small delay to ensure message finishes playing before hangup
            await asyncio.sleep(2)
        
        await hangup_call()
        logging.info("Call has been successfully terminated.")

    except Exception as e:
        # Catch errors during the main agent loop
        logging.error(f"Error during agent execution: {e}", exc_info=True)
        # Attempt graceful hangup even if error occurs
        try:
            await hangup_call()
        except Exception as hangup_err:
            logging.error(f"Error during final hangup attempt: {hangup_err}")

    finally:
        # --- UPLOAD RECORDING LOGIC (runs after call ends or errors) ---
        if UPLOAD_ENABLED and egress_id and lkapi and LIVEKIT_API_AVAILABLE:
            logging.info(f"Checking status for egress_id: {egress_id} after call ended.")
            final_filepath_on_host = None  # Track the file path for deletion
            try:
                logging.info(f"Waiting {EGRESS_CHECK_DELAY_SECONDS}s for Egress finalization...")
                await asyncio.sleep(EGRESS_CHECK_DELAY_SECONDS)

                list_resp = await lkapi.egress.list_egress(ListEgressRequest(egress_id=egress_id))

                if list_resp.items:
                    egress_info = list_resp.items[0]
                    logging.info(f"Final Egress Status: {egress_info.status}")  # Log numerical status
                    
                    # Convert numerical status to enum for comparison
                    status_enum = EgressStatus(egress_info.status)
                    
                    if status_enum == EgressStatus.EGRESS_COMPLETE:
                        logging.info(f"Egress {egress_id} completed successfully.")
                        if egress_info.files:
                            # Use the filename reported by the API results
                            final_filename_base = os.path.basename(egress_info.files[0].filename)
                            logging.info(f"Egress reported final filename: {final_filename_base}")

                            # Construct the FULL path ON THE HOST where the file should be
                            final_filepath_on_host = os.path.join(RECORDINGS_HOST_PATH, final_filename_base)
                            logging.info(f"Expecting file at host path: {final_filepath_on_host}")

                            upload_response = await upload_recording(final_filepath_on_host, UPLOAD_API_URL)

                            # --- SAVE UPLOAD RESPONSE TO DB ---
                            if upload_response and upload_response.get("success"):
                                upload_response_data = upload_response.get("data")
                                if upload_response_data:
                                    try:
                                        # Save recording URL and metadata to session (if session_manager exists)
                                        if 'session_manager' in locals():
                                            await session_manager.update_session_with_recording(upload_response_data)
                                            logging.info(f"Recording URL saved to database: {upload_response_data.get('url')}")
                                        else:
                                            logging.warning("SessionManager not available - recording URL not saved to database")
                                    except Exception as db_update_err:
                                        logging.error(f"Failed to save recording info to database: {db_update_err}", exc_info=True)

                                    # --- CRM CALL-DATA UPLOAD ---
                                    if CRM_UPLOAD_ENABLED:
                                        try:
                                            await upload_call_data_to_crm(
                                                recording_url=upload_response_data.get('url'),
                                                recording_size=upload_response_data.get('size'),
                                                dialed_number=dialed_number,
                                                full_config=full_config,
                                                session_manager=session_manager if 'session_manager' in locals() else None
                                            )
                                        except Exception as crm_upload_err:
                                            logging.error(f"Failed to upload call data to CRM: {crm_upload_err}", exc_info=True)
                                    else:
                                        logging.info("CRM upload disabled - skipping call data upload")

                            if upload_response and DELETE_LOCAL_AFTER_UPLOAD:
                                await delete_local_file(final_filepath_on_host)
                            elif not upload_response:
                                logging.error(f"Upload failed for {final_filename_base}. Local file kept (if deletion enabled).")

                        else:
                            logging.warning(f"Egress {egress_id} completed but reported no files.")
                    elif status_enum == EgressStatus.EGRESS_FAILED:
                        logging.error(f"Egress {egress_id} failed. Reason: {egress_info.error}. No upload attempted.")
                    else:
                        logging.warning(f"Egress {egress_id} finished with status: {status_enum}. No upload attempted.")
                else:
                    logging.warning(f"Could not retrieve final status for egress_id: {egress_id}")

            except Exception as e:
                logging.error(f"Error checking egress status or uploading recording: {e}", exc_info=True)
            finally:
                # Now close the API client session
                if lkapi and LIVEKIT_API_AVAILABLE:
                    await lkapi.aclose()
                    logging.info("LiveKit API client closed.")
                # Delete local file even if upload fails but deletion is enabled and path known
                if DELETE_LOCAL_AFTER_UPLOAD and final_filepath_on_host and not upload_response:
                    logging.warning(f"Attempting to delete local file {final_filepath_on_host} after failed upload...")
                    await delete_local_file(final_filepath_on_host)
                     
        elif lkapi and LIVEKIT_API_AVAILABLE:
            # Close client if recording wasn't started but client was created
            await lkapi.aclose()
            logging.info("LiveKit API client closed (recording was not started).")

        logging.info("Agent entrypoint finished.")


if __name__ == "__main__":
    # --- Corrected: Call run_app only once ---
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="friday-assistant"
        )
    )
