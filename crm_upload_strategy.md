# CRM Upload Strategy Documentation

## Overview
This document outlines the current state and proposed strategy for CRM upload functionality in the LiveKit voice bot system.

## Current State Analysis

### Existing Files Structure
- **`backup.py`**: Working version with correct recording logic and imports
- **`cagent.py`**: Simplified version created from backup.py 
- **`crm_upload.py`**: Contains `upload_call_data_from_conversation` function
- **APIs**: 
  - Recording upload: `https://devcrm.xeny.ai/apis/api/public/upload` (Form data)
  - CRM data upload: `https://devcrm.xeny.ai/apis/api/public/call-data` (JSON)

### Current Recording Logic (Working in backup.py)

```python
# Recording Block - Line ~380-430
try:
    lkapi = LiveKitAPI(http_host, livekit_api_key, livekit_api_secret)
    filename = f"recordings/{ctx.room.name}-{int(time.time())}"
    file_output = EncodedFileOutput(filepath=filename)
    request = RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[file_output]
    )
    info = await lkapi.egress.start_room_composite_egress(request)
    logging.info(f"Successfully started recording. Egress ID: {info.egress_id}, File: {filename}")
except Exception as e:
    logging.error(f"Failed to start recording: {e}")
finally:
    if lkapi:
        await lkapi.aclose()  # ❌ ISSUE: Client closed too early
```

### Current CRM Upload Logic Issues

#### Problem 1: Scope and Timing Issues
- `egress_id` variable goes out of scope after recording block
- `lkapi` client is closed immediately after recording starts
- Upload logic tries to use closed client in `finally` block

#### Problem 2: Missing Imports and Variables
```python
# Missing imports in backup.py:
from livekit.protocol import EgressStatus  # ❌ Not imported
LIVEKIT_API_AVAILABLE = True  # ❌ Variable not defined
```

#### Problem 3: Logic Flow Problems
```
Current Flow (BROKEN):
Recording Start → Close API Client → Upload Logic (uses closed client) ❌

Required Flow (CORRECT):
Recording Start → Call Processing → Upload Logic → Close API Client ✅
```

### Current CRM Upload Function

```python
async def upload_call_data_to_crm(
    recording_url: str,
    recording_size: int,
    dialed_number: str,
    full_config: dict,
    session_manager=None
):
    # Extract campaign details from persona config
    campaign_id = full_config.get("campaigns", [{}])[0].get("_id")
    voice_agent_id = full_config.get("campaigns", [{}])[0].get("voiceAgents", [{}])[0].get("_id")
    client_id = full_config.get("campaigns", [{}])[0].get("client")
    
    # Generate call metadata
    call_id = f"CALL-{timestamp}-{dialed_number.replace('+', '')[-8:]}"
    
    # Call external CRM upload function
    success = await asyncio.to_thread(
        upload_call_data_from_session,  # From crm_upload.py
        campaign_id=campaign_id,
        voice_agent_id=voice_agent_id,
        client_id=client_id,
        call_id=call_id,
        caller_phone=dialed_number,
        # ... other parameters
    )
```

### Expected CRM Payload Format

```json
{
    "campaignId": "string",
    "voiceAgentId": "string", 
    "client": "string",
    "callDetails": {
        "callId": "CALL-20251029-12345678",
        "direction": "inbound",
        "startTime": "2025-10-29T10:00:00Z",
        "endTime": "2025-10-29T10:05:00Z", 
        "duration": 300,
        "status": "completed",
        "callerNumber": "+918655066243",
        "recordingUrl": "https://devcrm.xeny.ai/uploads/recording.ogg",
        "recordingDuration": 300,
        "recordingSize": 1234567
    },
    "caller": {
        "phoneNumber": "+918655066243"
    },
    "transcription": {
        "session_id": "livekit-20251029-113920",
        "start_time": "2025-10-29T10:00:00Z",
        "end_time": "2025-10-29T10:05:00Z",
        "duration_seconds": 300,
        "total_items": 25,
        "conversation_items": [
            {
                "role": "user|assistant",
                "content": "conversation text",
                "timestamp": "2025-10-29T10:01:00Z",
                "source": "livekit-session",
                "transcript_confidence": null
            }
        ],
        "lead_generated": true,
        "metadata": {
            "auto_saved": true
        }
    },
    "lead": {}
}
```

## Proposed Solutions Analysis

### Approach 1: Global Call Metadata Variable

**Implementation:**
```python
class CallMetadata:
    def __init__(self):
        self.egress_id = None
        self.lkapi = None  # Keep API client alive
        self.conversation_id = None
        self.lead_id = None
        self.dialed_number = None
        self.full_config = None
        self.session_manager = None
        self.recording_filename = None
        self.call_start_time = None

# Global instance
call_meta = CallMetadata()
```

**Advantages:**
- ✅ Clean & Direct variable access
- ✅ Efficient - no parsing required
- ✅ Reliable - data guaranteed available
- ✅ Type Safety - proper data types
- ✅ Fits single-call-per-process architecture

**Disadvantages:**
- ❌ Potential concurrent call issues (mitigated by process isolation)
- ❌ Memory usage for entire process lifetime
- ❌ State management between calls

### Approach 2: Log Parsing & Extraction

**Implementation:**
```python
# Extract from logs:
# "Successfully started recording. Egress ID: EG_xyz, File: filename"
# "Lead created with ID: 6900ac26995436dc7dd9abaa"
# "Session created with ID: 6900ac4c995436dc7dd9abb4"

import re
def extract_egress_id_from_logs():
    with open("sessions.log", "r") as f:
        for line in f:
            match = re.search(r"Egress ID: (\w+)", line)
            if match:
                return match.group(1)
```

**Advantages:**
- ✅ No memory usage in RAM
- ✅ Complete audit trail
- ✅ Concurrent safe (file-based)
- ✅ Debugging friendly

**Disadvantages:**
- ❌ Complex parsing logic required
- ❌ Performance overhead (file I/O)
- ❌ Reliability depends on log format
- ❌ Race conditions with multiple processes

### Approach 3: Enhanced Storage Strategy (RECOMMENDED)

**Implementation:**
```python
# 1. Enhance SessionManager to store recording metadata
class SessionManager:
    def set_recording_metadata(self, metadata):
        self.recording_metadata = metadata
        # Store in MongoDB/file
    
    def get_recording_metadata(self):
        return self.recording_metadata

# 2. Modified recording block
if session_manager:
    session_manager.set_recording_metadata({
        "egress_id": info.egress_id,
        "recording_filename": filename,
        "recording_start_time": datetime.now().isoformat(),
        "lkapi_reference": lkapi  # Keep client alive
    })

# 3. Enhanced data structure
session_data = {
    "session_id": "session_20251029_113920_abc123",
    "egress_id": "EG_xyz789",
    "dialed_number": "+918655066243",
    "recording_filename": "recordings/number-_918655066243-1698567890",
    "conversation_items": [...],
    "leads": [...],
    "metadata": {
        "recording_start_time": "2025-10-29T11:39:20Z",
        "call_start_time": "2025-10-29T11:39:19Z"
    }
}

# 4. Modified upload logic
if session_manager:
    recording_metadata = session_manager.get_recording_metadata()
    if recording_metadata and recording_metadata.get("egress_id"):
        egress_id = recording_metadata["egress_id"]
        lkapi = recording_metadata["lkapi_reference"]
        # Proceed with upload workflow
```

**Advantages:**
- ✅ Leverages existing SessionManager infrastructure
- ✅ Data integrity through linked IDs
- ✅ Retrieval flexibility (query by any ID)
- ✅ Complete audit trail
- ✅ Concurrent safe (session-based)
- ✅ No global variables
- ✅ Future-proof design

**Disadvantages:**
- ❌ Requires SessionManager modifications
- ❌ Slightly more complex implementation

## Recommended Implementation Strategy

### Phase 1: Fix Immediate Issues
1. **Add missing imports to backup.py:**
   ```python
   from livekit.protocol import EgressStatus
   LIVEKIT_API_AVAILABLE = True
   ```

2. **Fix API client lifecycle:**
   ```python
   # Don't close lkapi immediately after recording
   # Keep reference for upload logic
   ```

3. **Fix variable scope issues:**
   ```python
   # Store egress_id in session metadata instead of local scope
   ```

### Phase 2: Enhance SessionManager
1. **Add recording metadata methods:**
   ```python
   def set_recording_metadata(self, metadata)
   def get_recording_metadata(self)
   def link_lead_to_session(self, lead_id)
   ```

2. **Enhance data storage structure:**
   ```python
   # Include egress_id in session documents
   # Link leads to sessions
   # Store recording filenames and URLs
   ```

### Phase 3: Implement Enhanced Upload Logic
1. **Modify upload workflow:**
   ```python
   # Query session for egress_id and metadata
   # Use session-stored lkapi reference
   # Build complete CRM payload from session data
   ```

2. **Add comprehensive error handling:**
   ```python
   # Fallback mechanisms if recording fails
   # Partial upload support
   # Retry logic for failed uploads
   ```

## Data Flow Diagram

```
Call Start
    ↓
Recording Start → Store egress_id in SessionManager
    ↓
Session Progress → Link session_id with egress_id
    ↓
Lead Creation → Reference session_id (contains egress_id)
    ↓
Call End → Query SessionManager for complete data
    ↓
Upload Recording (Form data to /upload)
    ↓
Upload CRM Data (JSON to /call-data)
    ↓
Cleanup and Close API Client
```

## Success Criteria

### Technical Requirements
- ✅ Recording files successfully uploaded to CRM storage
- ✅ Call data successfully uploaded to CRM database
- ✅ All session data (transcript, leads, recording) linked correctly
- ✅ No scope/variable issues in upload logic
- ✅ Proper API client lifecycle management

### Data Integrity Requirements
- ✅ Every recording has corresponding CRM data entry
- ✅ Session IDs link recordings to transcripts and leads
- ✅ Complete audit trail from call start to CRM upload
- ✅ Error handling for partial failures

### Performance Requirements
- ✅ Upload process completes within 30 seconds of call end
- ✅ No memory leaks from persistent data storage
- ✅ Efficient data retrieval for upload processing

## Implementation Status Update

### ✅ COMPLETED - Phase 1: Fix Immediate Issues
1. **Added missing imports to backup.py:**
   ```python
   from livekit.protocol import EgressStatus
   LIVEKIT_API_AVAILABLE = True
   ```

2. **Fixed API client lifecycle:**
   - Removed immediate `lkapi.aclose()` after recording start
   - Keep API client reference in SessionManager for upload logic
   - Proper cleanup in finally block after upload completes

3. **Fixed variable scope issues:**
   - Store egress_id in SessionManager metadata instead of local scope
   - Enhanced filename with proper .ogg extension
   - Initialize variables outside try blocks for proper scope management

### ✅ COMPLETED - Phase 2: Enhanced SessionManager
1. **Added recording metadata methods:**
   ```python
   def set_recording_metadata(self, metadata)  # Store egress_id, filename, API client
   def get_recording_metadata(self)            # Retrieve recording data
   def set_call_metadata(self, metadata)       # Store dialed_number, campaign info
   def get_call_metadata(self)                 # Retrieve call data
   def link_lead_to_session(self, lead_id)     # Link lead to session
   def get_complete_session_data(self)         # Get all data for CRM upload
   ```

2. **Enhanced data storage structure:**
   ```python
   recording_metadata = {
       "egress_id": "EG_xyz789",
       "recording_filename": "recordings/room-timestamp.ogg",
       "recording_start_time": "2025-10-29T11:39:20Z",
       "lkapi_reference": lkapi  # Keep client alive
   }
   
   call_metadata = {
       "dialed_number": "+918655066243",
       "full_config": {...},
       "campaign_id": "campaign_123",
       "voice_agent_id": "agent_456",
       "client_id": "client_789",
       "call_start_time": "2025-10-29T11:39:19Z"
   }
   ```

### ✅ COMPLETED - Phase 3: Enhanced Upload Logic
1. **Modified upload workflow:**
   - Query SessionManager for egress_id and API client reference
   - Use EgressInfo.files[0].filename from API response (per LiveKit docs)
   - Build complete CRM payload from SessionManager data
   - Proper fallback handling if SessionManager data unavailable

2. **Added comprehensive error handling:**
   - Fallback mechanisms if recording fails
   - Enhanced error logging with stack traces
   - Guaranteed API client cleanup even on errors
   - Graceful degradation to local variables if needed

### 🔄 IN PROGRESS - Lead Linking Enhancement
**Current State:** `create_lead` tool is available in Assistant but needs linking mechanism.

**Next Step:** Modify tools.py or create a monitoring mechanism to capture lead IDs when created and link them to SessionManager.

**Current Implementation:** Lead data will be captured in transcript logs and available for CRM upload through session history.

## Updated Data Flow

```
Call Start
    ↓
Recording Start → Store egress_id + API client in SessionManager.recording_metadata
    ↓
Session Setup → Store dialed_number + campaign info in SessionManager.call_metadata
    ↓
Agent Conversation → Tools (create_lead, detect_intent) operate normally
    ↓
Call End → SessionManager.get_complete_session_data() for CRM upload
    ↓
Upload Recording → Use SessionManager.recording_metadata.egress_id
    ↓
Upload CRM Data → Use SessionManager.call_metadata for campaign info
    ↓
API Client Cleanup → Close SessionManager.recording_metadata.lkapi_reference
```

## Next Steps

1. **✅ COMPLETED** - Enhanced SessionManager Implementation
2. **✅ COMPLETED** - Recording Block Modification with proper file extensions
3. **✅ COMPLETED** - Upload Logic Update using SessionManager data
4. **🔄 REMAINING** - Lead ID capture and linking (optional enhancement)
5. **🔄 REMAINING** - Production testing and validation

---

**Document Status**: Implementation Complete - Ready for Testing
**Last Updated**: October 29, 2025
**Author**: System Implementation
**Implementation Notes**: Core enhanced storage strategy successfully implemented with comprehensive error handling and fallback mechanisms.