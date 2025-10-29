#!/usr/bin/env python3
"""
Test script to debug LiveKit Egress protobuf object structure
This helps understand the correct field names for egress_info access
"""

import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_egress_protobuf_access():
    """Test egress protobuf object access patterns"""
    try:
        from livekit.api import LiveKitAPI, ListEgressRequest
        from livekit.protocol.egress import EgressStatus
        
        logging.info("✅ LiveKit API imports successful")
        
        # Test enum values
        logging.info("=== Egress Status Enum Values ===")
        for status_name in dir(EgressStatus):
            if not status_name.startswith('_'):
                try:
                    status_value = getattr(EgressStatus, status_name)
                    logging.info(f"{status_name} = {status_value}")
                except:
                    pass
        
        # Test status mapping
        logging.info("=== Status Value Mapping ===")
        status_names = {
            0: "EGRESS_STARTING",
            1: "EGRESS_ACTIVE", 
            2: "EGRESS_ENDING",
            3: "EGRESS_COMPLETE",
            4: "EGRESS_FAILED",
            5: "EGRESS_ABORTED",
            6: "EGRESS_LIMIT_REACHED"
        }
        
        for value, name in status_names.items():
            logging.info(f"Status {value}: {name}")
        
        logging.info("=== Protobuf Field Guide ===")
        logging.info("Common egress_info fields:")
        logging.info("- egress_info.egress_id")
        logging.info("- egress_info.room_id") 
        logging.info("- egress_info.room_name")
        logging.info("- egress_info.status (numeric value)")
        logging.info("- egress_info.started_at")
        logging.info("- egress_info.ended_at")
        logging.info("- egress_info.file_results (list of file objects)")
        logging.info("- egress_info.error (if failed)")
        
        logging.info("Common file_result fields:")
        logging.info("- file_result.filename")
        logging.info("- file_result.location") 
        logging.info("- file_result.size")
        logging.info("- file_result.download_url (if available)")
        
    except ImportError as e:
        logging.error(f"❌ Could not import LiveKit API: {e}")
        logging.error("Please run: pip install livekit-api")
    except Exception as e:
        logging.error(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    logging.info("🔍 Testing LiveKit Egress protobuf access...")
    test_egress_protobuf_access()
    logging.info("✅ Test completed")