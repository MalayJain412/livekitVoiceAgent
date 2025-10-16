#!/usr/bin/env python3
"""
Data Migration Script for Friday AI
Migrates existing leads and conversations from local files to MongoDB

Usage:
    python migrate_to_mongodb.py [--dry-run] [--leads-only] [--conversations-only]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from db_config import LeadsDB, ConversationDB, TranscriptDB, validate_environment
except ImportError as e:
    print(f"Error: Cannot import MongoDB modules. Please install requirements: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DataMigrator:
    """Handles migration of existing data to MongoDB"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.leads_migrated = 0
        self.conversations_migrated = 0
        self.transcript_events_migrated = 0
        self.errors = []
        
        # Paths
        self.leads_dir = Path("leads")
        self.conversations_dir = Path("conversations")
        self.transcripts_file = self.conversations_dir / "transcripts.jsonl"
        
        if dry_run:
            logging.info("DRY RUN MODE - No data will be written to MongoDB")
    
    def migrate_leads(self) -> bool:
        """Migrate lead JSON files to MongoDB"""
        logging.info("Starting leads migration...")
        
        if not self.leads_dir.exists():
            logging.warning(f"Leads directory {self.leads_dir} does not exist")
            return True
        
        lead_files = list(self.leads_dir.glob("lead_*.json"))
        logging.info(f"Found {len(lead_files)} lead files to migrate")
        
        for lead_file in lead_files:
            try:
                with open(lead_file, 'r', encoding='utf-8') as f:
                    lead_data = json.load(f)
                
                # Convert timestamp string to datetime if needed
                if isinstance(lead_data.get('timestamp'), str):
                    try:
                        lead_data['timestamp'] = datetime.fromisoformat(lead_data['timestamp'])
                    except ValueError:
                        lead_data['timestamp'] = datetime.utcnow()
                
                if self.dry_run:
                    logging.info(f"Would migrate lead: {lead_data.get('name', 'Unknown')} ({lead_data.get('email', 'No email')})")
                else:
                    # Check if lead already exists
                    existing = LeadsDB.get_lead_by_email(lead_data.get('email', ''))
                    if existing:
                        logging.info(f"Lead already exists: {lead_data.get('email')}")
                        continue
                    
                    # Create lead
                    lead_id = LeadsDB.create_lead(lead_data)
                    if lead_id:
                        logging.info(f"Migrated lead: {lead_file.name} -> {lead_id}")
                        self.leads_migrated += 1
                    else:
                        self.errors.append(f"Failed to create lead from {lead_file.name}")
                
            except Exception as e:
                error_msg = f"Error processing {lead_file.name}: {e}"
                logging.error(error_msg)
                self.errors.append(error_msg)
        
        logging.info(f"Leads migration completed: {self.leads_migrated} migrated")
        return True
    
    def migrate_transcript_events(self) -> bool:
        """Migrate JSONL transcript events to MongoDB"""
        logging.info("Starting transcript events migration...")
        
        if not self.transcripts_file.exists():
            logging.warning(f"Transcripts file {self.transcripts_file} does not exist")
            return True
        
        try:
            with open(self.transcripts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            logging.info(f"Found {len(lines)} transcript events to migrate")
            
            for i, line in enumerate(lines):
                try:
                    event_data = json.loads(line.strip())
                    
                    # Convert timestamp string to datetime if needed
                    if isinstance(event_data.get('timestamp'), str):
                        try:
                            timestamp_str = event_data['timestamp'].rstrip('Z')
                            event_data['timestamp'] = datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            event_data['timestamp'] = datetime.utcnow()
                    
                    # Generate session ID based on timestamp for grouping
                    timestamp = event_data.get('timestamp', datetime.utcnow())
                    session_id = f"migrated_{timestamp.strftime('%Y%m%d_%H')}"
                    
                    if self.dry_run:
                        logging.info(f"Would migrate event {i+1}: {event_data.get('role', 'unknown')} - {event_data.get('content', '')[:50]}...")
                    else:
                        success = TranscriptDB.log_event(event_data, session_id)
                        if success:
                            self.transcript_events_migrated += 1
                        else:
                            self.errors.append(f"Failed to migrate event {i+1}")
                    
                    if (i + 1) % 100 == 0:
                        logging.info(f"Processed {i + 1} transcript events...")
                
                except Exception as e:
                    error_msg = f"Error processing transcript event {i+1}: {e}"
                    logging.error(error_msg)
                    self.errors.append(error_msg)
            
            logging.info(f"Transcript events migration completed: {self.transcript_events_migrated} migrated")
            return True
            
        except Exception as e:
            error_msg = f"Error reading transcripts file: {e}"
            logging.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def migrate_conversation_sessions(self) -> bool:
        """Migrate conversation session JSON files to MongoDB"""
        logging.info("Starting conversation sessions migration...")
        
        if not self.conversations_dir.exists():
            logging.warning(f"Conversations directory {self.conversations_dir} does not exist")
            return True
        
        # Find all session files
        session_files = list(self.conversations_dir.glob("transcript_session_*.json"))
        conversation_files = list(self.conversations_dir.glob("conversation_*.json"))
        all_session_files = session_files + conversation_files
        
        logging.info(f"Found {len(all_session_files)} conversation session files to migrate")
        
        for session_file in all_session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # Generate session_id if not present
                if 'session_id' not in session_data:
                    session_data['session_id'] = f"migrated_{session_file.stem}"
                
                # Convert timestamp fields
                for field in ['start_time', 'end_time', 'timestamp']:
                    if field in session_data and isinstance(session_data[field], str):
                        try:
                            session_data[field] = datetime.fromisoformat(session_data[field].replace('Z', ''))
                        except ValueError:
                            session_data[field] = datetime.utcnow()
                
                # Add missing fields
                if 'total_items' not in session_data and 'items' in session_data:
                    session_data['total_items'] = len(session_data['items'])
                
                if 'duration_seconds' not in session_data:
                    start = session_data.get('start_time')
                    end = session_data.get('end_time')
                    if start and end:
                        session_data['duration_seconds'] = (end - start).total_seconds()
                    else:
                        session_data['duration_seconds'] = 0
                
                if 'lead_generated' not in session_data:
                    # Check if any items indicate lead generation
                    items = session_data.get('items', [])
                    session_data['lead_generated'] = any(
                        item.get('type') == 'function_call' and item.get('name') == 'create_lead'
                        for item in items if isinstance(item, dict)
                    )
                
                if self.dry_run:
                    logging.info(f"Would migrate session: {session_file.name} -> {session_data.get('session_id')}")
                else:
                    # Check if session already exists
                    existing = ConversationDB.get_session(session_data['session_id'])
                    if existing:
                        logging.info(f"Session already exists: {session_data['session_id']}")
                        continue
                    
                    # Create session
                    session_id = ConversationDB.create_session(session_data)
                    if session_id:
                        logging.info(f"Migrated session: {session_file.name} -> {session_id}")
                        self.conversations_migrated += 1
                    else:
                        self.errors.append(f"Failed to create session from {session_file.name}")
                
            except Exception as e:
                error_msg = f"Error processing {session_file.name}: {e}"
                logging.error(error_msg)
                self.errors.append(error_msg)
        
        logging.info(f"Conversation sessions migration completed: {self.conversations_migrated} migrated")
        return True
    
    def run_migration(self, migrate_leads: bool = True, migrate_conversations: bool = True) -> bool:
        """Run the complete migration process"""
        logging.info("Starting data migration to MongoDB...")
        
        # Test MongoDB connection
        if not self.dry_run:
            try:
                if not validate_environment():
                    logging.error("MongoDB connection validation failed")
                    return False
            except Exception as e:
                logging.error(f"MongoDB validation error: {e}")
                return False
        
        success = True
        
        # Migrate leads
        if migrate_leads:
            success &= self.migrate_leads()
        
        # Migrate conversations
        if migrate_conversations:
            success &= self.migrate_transcript_events()
            success &= self.migrate_conversation_sessions()
        
        # Report results
        logging.info("=== Migration Summary ===")
        if not self.dry_run:
            logging.info(f"Leads migrated: {self.leads_migrated}")
            logging.info(f"Transcript events migrated: {self.transcript_events_migrated}")
            logging.info(f"Conversation sessions migrated: {self.conversations_migrated}")
        else:
            logging.info("DRY RUN completed - no data was written to MongoDB")
        
        if self.errors:
            logging.error(f"Errors encountered: {len(self.errors)}")
            for error in self.errors[:10]:  # Show first 10 errors
                logging.error(f"  - {error}")
            if len(self.errors) > 10:
                logging.error(f"  ... and {len(self.errors) - 10} more errors")
        
        return success and len(self.errors) == 0

def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description="Migrate Friday AI data to MongoDB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without writing to MongoDB")
    parser.add_argument("--leads-only", action="store_true", help="Migrate only leads")
    parser.add_argument("--conversations-only", action="store_true", help="Migrate only conversations")
    
    args = parser.parse_args()
    
    # Determine what to migrate
    migrate_leads = not args.conversations_only
    migrate_conversations = not args.leads_only
    
    # Create migrator and run
    migrator = DataMigrator(dry_run=args.dry_run)
    success = migrator.run_migration(
        migrate_leads=migrate_leads,
        migrate_conversations=migrate_conversations
    )
    
    if success:
        logging.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logging.error("Migration completed with errors!")
        sys.exit(1)

if __name__ == "__main__":
    main()