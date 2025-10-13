#!/usr/bin/env python3
"""
Test MongoDB Integration for Friday AI
Validates MongoDB connection, data operations, and migration functionality

Usage:
    python test_mongodb_integration.py [--install-deps] [--skip-connection]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MongoDBTester:
    """Test suite for MongoDB integration"""
    
    def __init__(self, skip_connection: bool = False):
        self.skip_connection = skip_connection
        self.test_results = {}
        self.test_session_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
    def test_imports(self) -> bool:
        """Test if MongoDB modules can be imported"""
        logging.info("Testing MongoDB imports...")
        
        try:
            import pymongo
            from pymongo import MongoClient
            self.test_results["imports"] = {"status": "PASS", "message": "All imports successful"}
            return True
        except ImportError as e:
            self.test_results["imports"] = {"status": "FAIL", "message": f"Import error: {e}"}
            logging.error(f"Import test failed: {e}")
            return False
    
    def test_db_config(self) -> bool:
        """Test database configuration module"""
        logging.info("Testing database configuration...")
        
        try:
            from db_config import validate_environment, test_connection
            
            if self.skip_connection:
                self.test_results["db_config"] = {"status": "SKIP", "message": "Connection test skipped"}
                return True
            
            # Test environment validation
            env_valid = validate_environment()
            
            if env_valid:
                self.test_results["db_config"] = {"status": "PASS", "message": "Environment validation successful"}
                return True
            else:
                self.test_results["db_config"] = {"status": "FAIL", "message": "Environment validation failed"}
                return False
                
        except Exception as e:
            self.test_results["db_config"] = {"status": "FAIL", "message": f"Configuration error: {e}"}
            logging.error(f"DB config test failed: {e}")
            return False
    
    def test_lead_operations(self) -> bool:
        """Test lead CRUD operations"""
        logging.info("Testing lead operations...")
        
        if self.skip_connection:
            self.test_results["lead_operations"] = {"status": "SKIP", "message": "Connection test skipped"}
            return True
        
        try:
            from db_config import LeadsDB
            
            # Test data
            test_lead = {
                "name": f"Test User {self.test_session_id}",
                "email": f"test_{self.test_session_id}@example.com",
                "company": "Test Company",
                "interest": "Test Product",
                "phone": "1234567890",
                "job_title": "Test Manager",
                "budget": "10k-50k",
                "timeline": "Q1 2024",
                "timestamp": datetime.utcnow(),
                "source": "Test Suite",
                "status": "new"
            }
            
            # Create lead
            lead_id = LeadsDB.create_lead(test_lead)
            if not lead_id:
                self.test_results["lead_operations"] = {"status": "FAIL", "message": "Failed to create test lead"}
                return False
            
            # Get lead by email
            retrieved_lead = LeadsDB.get_lead_by_email(test_lead["email"])
            if not retrieved_lead:
                self.test_results["lead_operations"] = {"status": "FAIL", "message": "Failed to retrieve test lead"}
                return False
            
            # Update lead status
            updated = LeadsDB.update_lead_status(test_lead["email"], "contacted")
            if not updated:
                self.test_results["lead_operations"] = {"status": "FAIL", "message": "Failed to update lead status"}
                return False
            
            # Verify update
            updated_lead = LeadsDB.get_lead_by_email(test_lead["email"])
            if updated_lead["status"] != "contacted":
                self.test_results["lead_operations"] = {"status": "FAIL", "message": "Lead status not updated correctly"}
                return False
            
            self.test_results["lead_operations"] = {
                "status": "PASS", 
                "message": f"All lead operations successful (ID: {lead_id})"
            }
            return True
            
        except Exception as e:
            self.test_results["lead_operations"] = {"status": "FAIL", "message": f"Lead operations error: {e}"}
            logging.error(f"Lead operations test failed: {e}")
            return False
    
    def test_transcript_operations(self) -> bool:
        """Test transcript event operations"""
        logging.info("Testing transcript operations...")
        
        if self.skip_connection:
            self.test_results["transcript_operations"] = {"status": "SKIP", "message": "Connection test skipped"}
            return True
        
        try:
            from db_config import TranscriptDB
            
            # Test events
            test_events = [
                {
                    "role": "user",
                    "content": "Hello, this is a test message",
                    "timestamp": datetime.utcnow(),
                    "source": "test_suite"
                },
                {
                    "role": "assistant", 
                    "content": "This is a test response",
                    "timestamp": datetime.utcnow(),
                    "source": "test_suite"
                }
            ]
            
            # Log events
            for event in test_events:
                success = TranscriptDB.log_event(event, self.test_session_id)
                if not success:
                    self.test_results["transcript_operations"] = {"status": "FAIL", "message": "Failed to log transcript event"}
                    return False
            
            # Retrieve events
            session_events = TranscriptDB.get_session_events(self.test_session_id)
            if len(session_events) < len(test_events):
                self.test_results["transcript_operations"] = {"status": "FAIL", "message": "Failed to retrieve all test events"}
                return False
            
            self.test_results["transcript_operations"] = {
                "status": "PASS",
                "message": f"Transcript operations successful ({len(session_events)} events)"
            }
            return True
            
        except Exception as e:
            self.test_results["transcript_operations"] = {"status": "FAIL", "message": f"Transcript operations error: {e}"}
            logging.error(f"Transcript operations test failed: {e}")
            return False
    
    def test_conversation_operations(self) -> bool:
        """Test conversation session operations"""
        logging.info("Testing conversation operations...")
        
        if self.skip_connection:
            self.test_results["conversation_operations"] = {"status": "SKIP", "message": "Connection test skipped"}
            return True
        
        try:
            from db_config import ConversationDB
            
            # Test session data
            test_session = {
                "session_id": self.test_session_id,
                "start_time": datetime.utcnow() - timedelta(minutes=10),
                "end_time": datetime.utcnow(),
                "items": [
                    {"role": "user", "content": "Test message 1"},
                    {"role": "assistant", "content": "Test response 1"}
                ],
                "total_items": 2,
                "duration_seconds": 600,
                "lead_generated": False,
                "metadata": {"test": True}
            }
            
            # Create session
            session_id = ConversationDB.create_session(test_session)
            if not session_id:
                self.test_results["conversation_operations"] = {"status": "FAIL", "message": "Failed to create test session"}
                return False
            
            # Retrieve session
            retrieved_session = ConversationDB.get_session(self.test_session_id)
            if not retrieved_session:
                self.test_results["conversation_operations"] = {"status": "FAIL", "message": "Failed to retrieve test session"}
                return False
            
            # Update session
            updated = ConversationDB.update_session(self.test_session_id, {
                "lead_generated": True,
                "metadata": {"test": True, "updated": True}
            })
            if not updated:
                self.test_results["conversation_operations"] = {"status": "FAIL", "message": "Failed to update test session"}
                return False
            
            self.test_results["conversation_operations"] = {
                "status": "PASS",
                "message": f"Conversation operations successful (ID: {session_id})"
            }
            return True
            
        except Exception as e:
            self.test_results["conversation_operations"] = {"status": "FAIL", "message": f"Conversation operations error: {e}"}
            logging.error(f"Conversation operations test failed: {e}")
            return False
    
    def test_queries(self) -> bool:
        """Test query utilities"""
        logging.info("Testing query utilities...")
        
        if self.skip_connection:
            self.test_results["queries"] = {"status": "SKIP", "message": "Connection test skipped"}
            return True
        
        try:
            from mongodb_queries import (
                LeadQueries, ConversationQueries, TranscriptQueries,
                get_lead_stats, get_conversation_stats
            )
            
            # Test lead queries
            lead_stats = get_lead_stats()
            recent_leads = LeadQueries.get_recent_leads(days=1)
            
            # Test conversation queries
            conv_stats = get_conversation_stats()
            recent_sessions = ConversationQueries.get_recent_sessions(days=1)
            
            # Test transcript queries
            transcript_stats = TranscriptQueries.get_transcript_stats()
            recent_events = TranscriptQueries.get_recent_events(hours=1)
            
            self.test_results["queries"] = {
                "status": "PASS",
                "message": f"Query utilities successful (stats: {bool(lead_stats)}, {bool(conv_stats)}, {bool(transcript_stats)})"
            }
            return True
            
        except Exception as e:
            self.test_results["queries"] = {"status": "FAIL", "message": f"Query utilities error: {e}"}
            logging.error(f"Query utilities test failed: {e}")
            return False
    
    def test_migration_dry_run(self) -> bool:
        """Test migration script in dry-run mode"""
        logging.info("Testing migration script (dry run)...")
        
        try:
            from migrate_to_mongodb import DataMigrator
            
            # Run dry run migration
            migrator = DataMigrator(dry_run=True)
            success = migrator.run_migration()
            
            self.test_results["migration"] = {
                "status": "PASS" if success else "FAIL",
                "message": f"Migration dry run {'successful' if success else 'failed'} (errors: {len(migrator.errors)})"
            }
            return success
            
        except Exception as e:
            self.test_results["migration"] = {"status": "FAIL", "message": f"Migration test error: {e}"}
            logging.error(f"Migration test failed: {e}")
            return False
    
    def test_tools_integration(self) -> bool:
        """Test tools.py integration with MongoDB"""
        logging.info("Testing tools.py MongoDB integration...")
        
        try:
            # Set MongoDB environment variable
            os.environ["USE_MONGODB"] = "true"
            
            # Import and test tools
            import tools
            
            # Check if MongoDB is available in tools
            if not hasattr(tools, 'MONGODB_AVAILABLE') or not tools.MONGODB_AVAILABLE:
                self.test_results["tools_integration"] = {"status": "SKIP", "message": "MongoDB not available in tools.py"}
                return True
            
            self.test_results["tools_integration"] = {
                "status": "PASS",
                "message": "Tools.py MongoDB integration successful"
            }
            return True
            
        except Exception as e:
            self.test_results["tools_integration"] = {"status": "FAIL", "message": f"Tools integration error: {e}"}
            logging.error(f"Tools integration test failed: {e}")
            return False
    
    def cleanup_test_data(self) -> bool:
        """Clean up test data from MongoDB"""
        if self.skip_connection:
            return True
            
        logging.info("Cleaning up test data...")
        
        try:
            from db_config import get_collection
            
            # Clean up test leads
            leads_collection = get_collection("leads")
            leads_collection.delete_many({"email": {"$regex": f"test_{self.test_session_id}"}})
            
            # Clean up test transcript events
            events_collection = get_collection("transcript_events")
            events_collection.delete_many({"session_id": self.test_session_id})
            
            # Clean up test conversation sessions
            sessions_collection = get_collection("conversation_sessions")
            sessions_collection.delete_many({"session_id": self.test_session_id})
            
            logging.info("Test data cleanup completed")
            return True
            
        except Exception as e:
            logging.error(f"Cleanup failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        logging.info(f"Starting MongoDB integration test suite (Session: {self.test_session_id})")
        
        tests = [
            ("Imports", self.test_imports),
            ("DB Config", self.test_db_config),
            ("Lead Operations", self.test_lead_operations),
            ("Transcript Operations", self.test_transcript_operations),
            ("Conversation Operations", self.test_conversation_operations),
            ("Query Utilities", self.test_queries),
            ("Migration Script", self.test_migration_dry_run),
            ("Tools Integration", self.test_tools_integration)
        ]
        
        results = []
        overall_success = True
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                results.append((test_name, success))
                if not success:
                    overall_success = False
            except Exception as e:
                logging.error(f"Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
                overall_success = False
        
        # Cleanup test data
        self.cleanup_test_data()
        
        # Print results
        self.print_test_results(results, overall_success)
        
        return overall_success
    
    def print_test_results(self, results: List[tuple], overall_success: bool):
        """Print formatted test results"""
        logging.info("=== MongoDB Integration Test Results ===")
        
        for test_name, success in results:
            status = self.test_results.get(test_name.lower().replace(" ", "_"), {})
            logging.info(f"{test_name}: {status.get('status', 'UNKNOWN')} - {status.get('message', 'No details')}")
        
        logging.info(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if not overall_success:
            logging.info("\nRecommendations:")
            logging.info("1. Ensure MongoDB server is running")
            logging.info("2. Install dependencies: pip install -r requirements.txt")
            logging.info("3. Set MONGODB_URI environment variable if using remote MongoDB")
            logging.info("4. Check MongoDB connection settings in db_config.py")

def install_dependencies():
    """Install required dependencies"""
    import subprocess
    
    logging.info("Installing MongoDB dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "pymongo", "dnspython"
        ])
        logging.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install dependencies: {e}")
        return False

def main():
    """Main test script entry point"""
    parser = argparse.ArgumentParser(description="Test MongoDB integration for Friday AI")
    parser.add_argument("--install-deps", action="store_true", help="Install MongoDB dependencies before testing")
    parser.add_argument("--skip-connection", action="store_true", help="Skip tests that require MongoDB connection")
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # Run tests
    tester = MongoDBTester(skip_connection=args.skip_connection)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()