#!/usr/bin/env python3
"""
Directory Upload Cron Script - Metadata-Based Matching
Scans conversations/, recordings/, and leads/ directories and uploads files to CRM.

This script implements the Metadata-Based Upload Strategy:
1. Scans for conversation files with embedded campaign metadata
2. Matches files by campaignId + voiceAgentId + sessionId 
3. Uploads recording file first to get URL
4. Uploads complete call data with recording URL
5. Tracks processed files to avoid re-upload

Usage:
    python upload_cron.py [--dry-run] [--batch-size=10] [--verbose]

Cron Setup:
    # Run every 5 minutes
    */5 * * * * cd /path/to/xeny-livekit-voicebot && python upload_cron.py >> upload_cron.log 2>&1
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import shutil
import re

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from crm_upload import upload_complete_call_data_sync
from mobile_api import extract_metadata_from_filename, match_files_by_metadata

class MetadataBasedUploadCron:
    """Metadata-based upload cron job using campaignId+voiceAgentId+sessionId matching"""
    
    def __init__(self, 
                 conversations_dir: str = "conversations",
                 recordings_dir: str = "recordings", 
                 leads_dir: str = "leads",
                 processed_dir: str = "processed_uploads",
                 batch_size: int = 10):
        
        self.conversations_dir = Path(conversations_dir)
        self.recordings_dir = Path(recordings_dir)
        self.leads_dir = Path(leads_dir)
        self.processed_dir = Path(processed_dir)
        self.batch_size = batch_size
        
        # Create processed directory if it doesn't exist
        self.processed_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "recordings_uploaded": 0,
            "call_data_uploaded": 0,
            "leads_uploaded": 0,
            "failed_uploads": 0,
            "skipped_files": 0
        }

    def get_unprocessed_conversations(self) -> List[Path]:
        """Get conversation files that haven't been uploaded yet"""
        
        if not self.conversations_dir.exists():
            logging.warning(f"Conversations directory not found: {self.conversations_dir}")
            return []
        
        # Get all conversation files (both metadata-based and timestamp-based)
        conversation_files = list(self.conversations_dir.glob("transcript_session_*.json"))
        
        # Filter out already processed files
        unprocessed = []
        for conv_file in conversation_files:
            processed_marker = self.processed_dir / f"{conv_file.name}.uploaded"
            
            if not processed_marker.exists():
                # Verify it's a valid conversation file
                if self.is_valid_conversation_file(conv_file):
                    unprocessed.append(conv_file)
                else:
                    logging.warning(f"Skipping invalid conversation file: {conv_file}")
                    self.stats["skipped_files"] += 1
        
        # Sort by modification time (oldest first)
        unprocessed.sort(key=lambda f: f.stat().st_mtime)
        
        logging.info(f"Found {len(unprocessed)} unprocessed conversation files")
        return unprocessed[:self.batch_size]

    def is_valid_conversation_file(self, conv_file: Path) -> bool:
        """Check if conversation file has valid format"""
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it has required format fields
            return (isinstance(data, dict) and 
                   'session_id' in data and 
                   'items' in data and
                   isinstance(data['items'], list))
                   
        except Exception as e:
            logging.error(f"Error validating conversation file {conv_file}: {e}")
            return False

    def find_matching_files_by_metadata(self, conv_file: Path) -> Tuple[Optional[Path], Optional[Path]]:
        """Find matching recording and lead files using metadata"""
        
        # Try metadata-based matching first
        conv_metadata = extract_metadata_from_filename(conv_file.name)
        
        if conv_metadata:
            logging.info(f"Using metadata matching for {conv_file.name}: {conv_metadata}")
            
            # Find matching recording - try metadata filename first, then egress mapping
            recording_file = None
            if self.recordings_dir.exists():
                # Method 1: Direct metadata filename matching
                for rec_file in self.recordings_dir.glob("*.ogg"):
                    rec_metadata = extract_metadata_from_filename(rec_file.name)
                    if rec_metadata and self._metadata_matches(conv_metadata, rec_metadata):
                        recording_file = rec_file
                        logging.info(f"Found matching recording by metadata: {rec_file.name}")
                        break
                
                # Method 2: Egress-based matching if no direct match found
                if not recording_file:
                    recording_file = self._find_recording_by_egress(conv_file)
                    if recording_file:
                        logging.info(f"Found matching recording by egress: {recording_file.name}")
            
            # Find matching lead
            lead_file = None
            if self.leads_dir.exists():
                for lead_f in self.leads_dir.glob("*.json"):
                    lead_metadata = extract_metadata_from_filename(lead_f.name)
                    if lead_metadata and self._metadata_matches(conv_metadata, lead_metadata):
                        lead_file = lead_f
                        logging.info(f"Found matching lead by metadata: {lead_f.name}")
                        break
            
            return recording_file, lead_file
        
        else:
            # Fallback to content-based metadata matching
            return self._find_matching_files_by_content(conv_file)

    def _find_recording_by_egress(self, conv_file: Path) -> Optional[Path]:
        """Find recording file using egress metadata mapping and phone number matching"""
        try:
            # Load conversation data to get phone number and timing
            with open(conv_file, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            # Get phone number from campaign metadata
            campaign_metadata = conv_data.get('metadata', {}).get('campaign_metadata', {})
            dialed_number = campaign_metadata.get('dialedNumber', '')
            
            if not dialed_number:
                logging.debug(f"No dialedNumber found in conversation metadata for {conv_file.name}")
                return None
            
            # Extract phone number without + prefix for room name matching
            phone_digits = dialed_number.lstrip('+')
            expected_room_pattern = f"number-_{phone_digits}"
            
            # Check all egress metadata files for matching room name
            if not self.recordings_dir.exists():
                return None
                
            for egress_file in self.recordings_dir.glob("EG_*.json"):
                try:
                    with open(egress_file, 'r', encoding='utf-8') as f:
                        egress_data = json.load(f)
                    
                    room_name = egress_data.get('room_name', '')
                    if room_name == expected_room_pattern:
                        # Extract recording filename from egress data
                        files = egress_data.get('files', [])
                        if files and files[0].get('filename'):
                            recording_filename = files[0]['filename']
                            
                            # Remove 'recordings/' prefix if present
                            if recording_filename.startswith('recordings/'):
                                recording_filename = recording_filename[11:]
                            
                            recording_path = self.recordings_dir / recording_filename
                            if recording_path.exists():
                                logging.info(f"Found recording via egress room matching: {room_name} -> {recording_filename}")
                                return recording_path
                            else:
                                logging.warning(f"Recording file not found at expected path: {recording_path}")
                                
                except Exception as e:
                    logging.error(f"Error reading egress file {egress_file}: {e}")
                    continue
            
            # Fallback: Try direct egress_id lookup if available
            egress_id = campaign_metadata.get('egressId')
            if egress_id:
                egress_file = self.recordings_dir / f"{egress_id}.json"
                if egress_file.exists():
                    with open(egress_file, 'r', encoding='utf-8') as f:
                        egress_data = json.load(f)
                    
                    files = egress_data.get('files', [])
                    if files and files[0].get('filename'):
                        recording_filename = files[0]['filename']
                        if recording_filename.startswith('recordings/'):
                            recording_filename = recording_filename[11:]
                        
                        recording_path = self.recordings_dir / recording_filename
                        if recording_path.exists():
                            logging.info(f"Found recording via direct egress ID: {egress_id} -> {recording_filename}")
                            return recording_path
            
            logging.debug(f"No matching recording found for {dialed_number} via egress mapping")
            return None
                
        except Exception as e:
            logging.error(f"Error finding recording by egress for {conv_file.name}: {e}")
            return None

    def _metadata_matches(self, metadata1: Dict[str, str], metadata2: Dict[str, str]) -> bool:
        """Check if two metadata dicts match on campaign+voice+session IDs"""
        key_fields = ['campaignId', 'voiceAgentId', 'sessionId']
        
        for field in key_fields:
            if metadata1.get(field) != metadata2.get(field):
                return False
        
        return True

    def _find_matching_files_by_content(self, conv_file: Path) -> Tuple[Optional[Path], Optional[Path]]:
        """Find matching files by looking inside conversation content for campaign metadata"""
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            # Extract campaign metadata from conversation content
            campaign_metadata = conv_data.get('metadata', {}).get('campaign_metadata', {})
            
            if campaign_metadata:
                campaign_id = campaign_metadata.get('campaignId')
                voice_agent_id = campaign_metadata.get('voiceAgentId')
                session_id = campaign_metadata.get('sessionId')
                
                logging.info(f"Using content metadata for {conv_file.name}: campaign={campaign_id}, voice={voice_agent_id}, session={session_id}")
                
                # Find matching files by checking their content
                recording_file = self._find_file_by_content_metadata(
                    self.recordings_dir, "*.ogg", campaign_metadata, "recording"
                )
                
                lead_file = self._find_file_by_content_metadata(
                    self.leads_dir, "*.json", campaign_metadata, "lead"
                )
                
                return recording_file, lead_file
            
        except Exception as e:
            logging.error(f"Error finding files by content for {conv_file}: {e}")
        
        return None, None

    def _find_file_by_content_metadata(self, directory: Path, pattern: str, 
                                     target_metadata: Dict, file_type: str) -> Optional[Path]:
        """Find file by checking its content for matching campaign metadata"""
        if not directory.exists():
            return None
        
        for file_path in directory.glob(pattern):
            try:
                if file_type == "recording":
                    # For .ogg files, we can't check content, so skip
                    continue
                elif file_type == "lead":
                    # Check lead file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    
                    file_metadata = file_data.get('campaign_metadata', {})
                    if self._metadata_matches(target_metadata, file_metadata):
                        return file_path
                        
            except Exception as e:
                logging.error(f"Error checking {file_type} file {file_path}: {e}")
                continue
        
        return None

    def extract_caller_phone_and_metadata(self, conversation_data: Dict) -> Tuple[str, Dict]:
        """Extract caller phone number and campaign metadata from conversation data"""
        try:
            # Method 1: Check embedded campaign metadata
            campaign_metadata = conversation_data.get('metadata', {}).get('campaign_metadata', {})
            caller_phone = campaign_metadata.get('dialedNumber', '')
            
            if caller_phone and campaign_metadata.get('campaignId'):
                logging.info(f"Found embedded campaign metadata: {campaign_metadata}")
                return caller_phone, {
                    "campaignId": campaign_metadata.get('campaignId'),
                    "voiceAgentId": campaign_metadata.get('voiceAgentId'),
                    "clientId": campaign_metadata.get('clientId')
                }
            
            # Method 2: Parse from conversation items
            for item in conversation_data.get('items', []):
                content = str(item.get('content', ''))
                # Look for phone number patterns
                phone_match = re.search(r'\+\d{10,15}', content)
                if phone_match:
                    caller_phone = phone_match.group(0)
                    break
            
            # Method 3: Default fallback
            if not caller_phone:
                caller_phone = "+919876543210"
            
            # For backward compatibility, return empty metadata if not found
            return caller_phone, {}
            
        except Exception as e:
            logging.error(f"Error extracting caller phone and metadata: {e}")
            return "+919876543210", {}

    def generate_call_id(self, conv_file: Path, campaign_metadata: Dict) -> str:
        """Generate unique call ID using metadata"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        if campaign_metadata.get('sessionId'):
            session_suffix = campaign_metadata['sessionId'][-8:] if len(campaign_metadata['sessionId']) > 8 else campaign_metadata['sessionId']
            return f"CALL-{timestamp}-{session_suffix}"
        else:
            # Fallback to file-based ID
            file_suffix = conv_file.stem[-8:] if len(conv_file.stem) > 8 else "00000000"
            return f"CALL-{timestamp}-{file_suffix}"

    def mark_as_processed(self, conv_file: Path, upload_result: Dict) -> None:
        """Mark conversation file as processed"""
        try:
            processed_marker = self.processed_dir / f"{conv_file.name}.uploaded"
            
            upload_info = {
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "original_path": str(conv_file),
                "upload_result": upload_result,
                "cron_run_time": datetime.now().isoformat()
            }
            
            with open(processed_marker, 'w', encoding='utf-8') as f:
                json.dump(upload_info, f, indent=2)
                
            logging.info(f"Marked as processed: {conv_file.name}")
            
        except Exception as e:
            logging.error(f"Error marking file as processed {conv_file}: {e}")

    def process_conversation_file(self, conv_file: Path, dry_run: bool = False) -> bool:
        """Process a single conversation file using metadata-based matching"""
        
        logging.info(f"Processing conversation file: {conv_file.name}")
        
        try:
            # Load conversation data
            with open(conv_file, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
            
            # Find matching recording and lead files using metadata
            recording_file, lead_file = self.find_matching_files_by_metadata(conv_file)
            
            # Extract call information and campaign metadata
            caller_phone, campaign_config = self.extract_caller_phone_and_metadata(conversation_data)
            call_id = self.generate_call_id(conv_file, campaign_config)
            
            # Use extracted campaign config or defaults
            campaign_id = campaign_config.get('campaignId') or os.getenv("DEFAULT_CAMPAIGN_ID", "68c91223fde0aa95caa3dbe4")
            voice_agent_id = campaign_config.get('voiceAgentId') or os.getenv("DEFAULT_VOICE_AGENT_ID", "68c9105cfde0aa95caa3db64")
            client_id = campaign_config.get('clientId') or os.getenv("DEFAULT_CLIENT_ID", "68c90d626052ee95ac77059d")
            
            logging.info(f"Call details: ID={call_id}, Phone={caller_phone}")
            logging.info(f"Campaign: {campaign_id}, Agent: {voice_agent_id}, Client: {client_id}")
            logging.info(f"Recording: {recording_file.name if recording_file else 'None'}")
            logging.info(f"Lead: {lead_file.name if lead_file else 'None'}")
            
            if dry_run:
                logging.info("DRY RUN: Would upload this call data")
                return True
            
            # Merge lead data into conversation if available
            if lead_file:
                try:
                    with open(lead_file, 'r', encoding='utf-8') as f:
                        lead_data = json.load(f)
                    conversation_data['lead'] = lead_data
                    conversation_data['lead_generated'] = True
                    self.stats["leads_uploaded"] += 1
                except Exception as e:
                    logging.error(f"Error loading lead file {lead_file}: {e}")
            
            # Upload complete call data (recording + call data)
            success = upload_complete_call_data_sync(
                campaign_id=campaign_id,
                voice_agent_id=voice_agent_id,
                client_id=client_id,
                call_id=call_id,
                caller_phone=caller_phone,
                conversation_data=conversation_data,
                recording_file_path=str(recording_file) if recording_file else None,
                direction="inbound",
                status="completed"
            )
            
            # Update statistics
            if success:
                self.stats["files_processed"] += 1
                self.stats["call_data_uploaded"] += 1
                if recording_file:
                    self.stats["recordings_uploaded"] += 1
                
                # Mark as processed
                upload_result = {
                    "success": True,
                    "call_id": call_id,
                    "recording_uploaded": bool(recording_file),
                    "lead_uploaded": bool(lead_file),
                    "campaign_metadata": campaign_config
                }
                self.mark_as_processed(conv_file, upload_result)
                
                logging.info(f"✅ Successfully processed: {conv_file.name}")
                return True
            else:
                self.stats["failed_uploads"] += 1
                logging.error(f"❌ Failed to upload: {conv_file.name}")
                return False
                
        except Exception as e:
            self.stats["failed_uploads"] += 1
            logging.error(f"❌ Error processing {conv_file}: {e}", exc_info=True)
            return False

    def run_scan_and_upload(self, dry_run: bool = False) -> Dict:
        """Main function: scan directories and upload files"""
        
        start_time = datetime.now()
        logging.info(f"Starting directory scan and upload (dry_run={dry_run})")
        
        # Reset statistics
        self.stats = {k: 0 for k in self.stats.keys()}
        
        # Get unprocessed conversation files
        conversation_files = self.get_unprocessed_conversations()
        
        if not conversation_files:
            logging.info("No unprocessed conversation files found")
            return self.stats
        
        logging.info(f"Processing {len(conversation_files)} conversation files (batch size: {self.batch_size})")
        
        # Process each conversation file
        for conv_file in conversation_files:
            try:
                self.process_conversation_file(conv_file, dry_run=dry_run)
            except Exception as e:
                logging.error(f"Unexpected error processing {conv_file}: {e}")
                self.stats["failed_uploads"] += 1
        
        # Calculate duration and success rate
        duration = (datetime.now() - start_time).total_seconds()
        total_attempts = self.stats["files_processed"] + self.stats["failed_uploads"]
        success_rate = (self.stats["files_processed"] / total_attempts * 100) if total_attempts > 0 else 0
        
        # Log summary
        logging.info(f"Upload scan completed in {duration:.1f}s:")
        logging.info(f"  Files processed: {self.stats['files_processed']}")
        logging.info(f"  Recordings uploaded: {self.stats['recordings_uploaded']}")
        logging.info(f"  Call data uploaded: {self.stats['call_data_uploaded']}")
        logging.info(f"  Leads uploaded: {self.stats['leads_uploaded']}")
        logging.info(f"  Failed uploads: {self.stats['failed_uploads']}")
        logging.info(f"  Success rate: {success_rate:.1f}%")
        
        # Add summary to stats
        self.stats.update({
            "duration_seconds": duration,
            "success_rate": success_rate,
            "timestamp": start_time.isoformat()
        })
        
        return self.stats

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler('upload_cron.log', mode='a')  # File output
        ]
    )

def main():
    """Main entry point for cron script"""
    
    parser = argparse.ArgumentParser(description='Directory Upload Cron Script')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (no actual uploads)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of files to process per run (default: 10)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--conversations-dir', default='conversations',
                       help='Path to conversations directory')
    parser.add_argument('--recordings-dir', default='recordings', 
                       help='Path to recordings directory')
    parser.add_argument('--leads-dir', default='leads',
                       help='Path to leads directory')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        # Create and run upload cron
        cron = MetadataBasedUploadCron(
            conversations_dir=args.conversations_dir,
            recordings_dir=args.recordings_dir,
            leads_dir=args.leads_dir,
            batch_size=args.batch_size
        )
        
        # Run scan and upload
        stats = cron.run_scan_and_upload(dry_run=args.dry_run)
        
        # Exit with appropriate code
        if stats["failed_uploads"] > 0:
            sys.exit(1)  # Signal failure for cron monitoring
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        logging.error(f"Fatal error in upload cron: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()