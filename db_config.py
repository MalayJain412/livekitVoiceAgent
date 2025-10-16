"""
MongoDB Configuration and Connection Management for Friday AI
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError

# Environment Variables for MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://malayjainttbs_db_user:zJhIUCpEhfah9gLP@cluster0.xhomp4e.mongodb.net/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "friday_ai")
MONGODB_TIMEOUT = int(os.getenv("MONGODB_TIMEOUT", "10000"))  # milliseconds - increased for Atlas

# Global MongoDB client and database instances
_client: Optional[MongoClient] = None
_database = None

class MongoDBConnection:
    """Singleton MongoDB connection manager"""
    
    def __init__(self):
        self.client = None
        self.database = None
        self.connected = False
    
    def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=MONGODB_TIMEOUT,
                connectTimeoutMS=MONGODB_TIMEOUT,
                socketTimeoutMS=MONGODB_TIMEOUT
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.database = self.client[MONGODB_DATABASE]
            self.connected = True
            
            # Ensure indexes are created
            self._create_indexes()
            
            logging.info(f"Successfully connected to MongoDB database: {MONGODB_DATABASE}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            self.connected = False
            return False
        except Exception as e:
            logging.error(f"Unexpected error connecting to MongoDB: {e}")
            self.connected = False
            return False
    
    def _create_indexes(self):
        """Create necessary indexes for collections"""
        try:
            # Leads collection indexes
            leads_collection = self.database.leads
            leads_collection.create_index("email", unique=True)
            leads_collection.create_index([("timestamp", pymongo.DESCENDING)])
            leads_collection.create_index("status")
            leads_collection.create_index("company")
            leads_collection.create_index("interest")
            
            # Transcript events collection indexes
            events_collection = self.database.transcript_events
            events_collection.create_index([("timestamp", pymongo.DESCENDING)])
            events_collection.create_index([("session_id", 1), ("timestamp", 1)])
            events_collection.create_index("role")
            
            # Conversation sessions collection indexes
            sessions_collection = self.database.conversation_sessions
            sessions_collection.create_index("session_id", unique=True)
            sessions_collection.create_index([("start_time", pymongo.DESCENDING)])
            sessions_collection.create_index("lead_generated")
            sessions_collection.create_index("lead_id")
            
            logging.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logging.warning(f"Error creating MongoDB indexes: {e}")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logging.info("MongoDB connection closed")
    
    def is_connected(self) -> bool:
        """Check if MongoDB connection is active"""
        if not self.connected or not self.client:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            self.connected = False
            return False

# Global connection instance
_connection = MongoDBConnection()

def get_database():
    """Get MongoDB database instance"""
    global _connection
    
    if not _connection.is_connected():
        if not _connection.connect():
            raise Exception("Unable to connect to MongoDB")
    
    return _connection.database

def get_collection(collection_name: str):
    """Get MongoDB collection"""
    db = get_database()
    return db[collection_name]

def close_connection():
    """Close MongoDB connection"""
    global _connection
    _connection.disconnect()

# Collection-specific helper functions
class LeadsDB:
    """Helper class for leads collection operations"""
    
    @staticmethod
    def create_lead(lead_data: Dict[str, Any]) -> Optional[str]:
        """Create a new lead in MongoDB"""
        try:
            collection = get_collection("leads")
            
            # Add timestamps
            now = datetime.utcnow()
            lead_data.update({
                "created_at": now,
                "updated_at": now
            })
            
            result = collection.insert_one(lead_data)
            logging.info(f"Lead created with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logging.warning(f"Lead with email {lead_data.get('email')} already exists")
            return None
        except Exception as e:
            logging.error(f"Error creating lead: {e}")
            return None
    
    @staticmethod
    def get_lead_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get lead by email address"""
        try:
            collection = get_collection("leads")
            return collection.find_one({"email": email})
        except Exception as e:
            logging.error(f"Error getting lead by email: {e}")
            return None
    
    @staticmethod
    def update_lead_status(email: str, status: str) -> bool:
        """Update lead status"""
        try:
            collection = get_collection("leads")
            result = collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error updating lead status: {e}")
            return False
    
    @staticmethod
    def get_leads_by_status(status: str, limit: int = 100) -> list:
        """Get leads by status"""
        try:
            collection = get_collection("leads")
            return list(collection.find({"status": status}).limit(limit))
        except Exception as e:
            logging.error(f"Error getting leads by status: {e}")
            return []

class TranscriptDB:
    """Helper class for transcript operations"""
    
    @staticmethod
    def log_event(event_data: Dict[str, Any], session_id: str = None) -> bool:
        """Log a transcript event"""
        try:
            collection = get_collection("transcript_events")
            
            # Add metadata
            event_data.update({
                "session_id": session_id or "default",
                "created_at": datetime.utcnow()
            })
            
            collection.insert_one(event_data)
            return True
            
        except Exception as e:
            logging.error(f"Error logging transcript event: {e}")
            return False
    
    @staticmethod
    def get_session_events(session_id: str) -> list:
        """Get all events for a session"""
        try:
            collection = get_collection("transcript_events")
            return list(collection.find({"session_id": session_id}).sort("timestamp", 1))
        except Exception as e:
            logging.error(f"Error getting session events: {e}")
            return []

class ConversationDB:
    """Helper class for conversation session operations"""
    
    @staticmethod
    def create_session(session_data: Dict[str, Any]) -> Optional[str]:
        """Create a new conversation session"""
        try:
            collection = get_collection("conversation_sessions")
            
            # Add timestamps
            now = datetime.utcnow()
            session_data.update({
                "created_at": now,
                "updated_at": now
            })
            
            result = collection.insert_one(session_data)
            logging.info(f"Session created with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Error creating conversation session: {e}")
            return None
    
    @staticmethod
    def update_session(session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update conversation session"""
        try:
            collection = get_collection("conversation_sessions")
            
            update_data["updated_at"] = datetime.utcnow()
            
            result = collection.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Error updating session: {e}")
            return False
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation session by ID"""
        try:
            collection = get_collection("conversation_sessions")
            return collection.find_one({"session_id": session_id})
        except Exception as e:
            logging.error(f"Error getting session: {e}")
            return None

# Test connection function
def test_connection() -> bool:
    """Test MongoDB connection and basic operations"""
    try:
        db = get_database()
        
        # Test basic operations
        test_collection = db.connection_test
        test_doc = {"test": True, "timestamp": datetime.utcnow()}
        
        result = test_collection.insert_one(test_doc)
        test_collection.delete_one({"_id": result.inserted_id})
        
        logging.info("MongoDB connection test successful")
        return True
        
    except Exception as e:
        logging.error(f"MongoDB connection test failed: {e}")
        return False

# Environment setup validation
def validate_environment():
    """Validate MongoDB environment configuration"""
    logging.info(f"MongoDB URI: {MONGODB_URI}")
    logging.info(f"MongoDB Database: {MONGODB_DATABASE}")
    logging.info(f"MongoDB Timeout: {MONGODB_TIMEOUT}ms")
    
    if "localhost" in MONGODB_URI:
        logging.warning("Using localhost MongoDB - ensure MongoDB server is running")
    
    return test_connection()