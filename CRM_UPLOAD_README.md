# CRM Upload Integration

This document explains how to use the CRM upload functionality to send call transcriptions and lead data to the CRM API.

## API Endpoint

The CRM upload uses the following endpoint:
```
POST https://devcrm.xeny.ai/apis/api/public/call-data
```

## Configuration

Set these environment variables to enable automatic CRM upload:

```bash
# Enable automatic upload after each call session
CRM_AUTO_UPLOAD=true

# Required CRM identifiers
CRM_CAMPAIGN_ID=68c91223fde0aa95caa3dbe4
CRM_VOICE_AGENT_ID=68c9105cfde0aa95caa3db64
CRM_CLIENT_ID=68c90d626052ee95ac77059d

# Default caller phone (used if not detected from call)
CRM_DEFAULT_CALLER_PHONE=+919876543210
```

## Payload Structure

The API expects this payload structure:

```json
{
  "campaignId": "68c91223fde0aa95caa3dbe4",
  "voiceAgentId": "68c9105cfde0aa95caa3db64", 
  "client": "68c90d626052ee95ac77059d",
  "callDetails": {
    "callId": "CALL-20250929-001",
    "direction": "inbound",
    "startTime": "2025-09-29T10:15:00.000Z",
    "endTime": "2025-09-29T10:20:30.000Z",
    "duration": 330,
    "status": "completed",
    "recordingUrl": "http://devcrm.xeny.ai/apis/uploads/recordings/1759173049893.wav",
    "recordingDuration": 330,
    "recordingSize": 2456789,
    "callerNumber": "+919876543210"
  },
  "caller": {
    "phoneNumber": "+919876543210"
  },
  "transcription": {
    "session_id": "session_20251023_075614_7e155942",
    "start_time": "2025-10-23 07:56:34.608343",
    "end_time": "2025-10-23 07:56:34.608343", 
    "duration_seconds": 30,
    "conversation_items": [
      {
        "role": "assistant",
        "content": "Namaste! Main Urban Piper se piperbot bol rahi hoon.",
        "timestamp": "2025-10-23T07:56:34.608343Z",
        "source": "agent"
      },
      {
        "role": "user", 
        "content": "Hello, I need help",
        "timestamp": "2025-10-23T07:56:44.608343Z",
        "transcript_confidence": 0.95,
        "source": "transcription_node"
      }
    ],
    "lead_generated": false,
    "metadata": {}
  },
  "lead": {
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Tech Corp", 
    "interest": "AI Solutions",
    "phone": "9876543210",
    "job_title": "CTO",
    "budget": "50k-100k",
    "timeline": "Q1 2025",
    "timestamp": "2025-10-23T07:56:34.608343Z",
    "source": "Friday AI Assistant",
    "status": "new"
  }
}
```

## Usage

### Automatic Upload

When `CRM_AUTO_UPLOAD=true`, the system automatically uploads call data when conversation sessions are saved in `transcript_logger.py`.

### Manual Upload Functions

#### Upload from Session Data
```python
from crm_upload import upload_call_data_from_session

success = upload_call_data_from_session(
    campaign_id="68c91223fde0aa95caa3dbe4",
    voice_agent_id="68c9105cfde0aa95caa3db64", 
    client_id="68c90d626052ee95ac77059d",
    call_id="CALL-001",
    caller_phone="+919876543210",
    transcript_data=transcript_dict,
    lead_data=lead_dict
)
```

#### Upload from Saved Files
```python
from crm_upload import upload_from_transcript_file

success = upload_from_transcript_file(
    transcript_file_path="conversations/transcript_session_2025-10-23T07-56-34.661114.json",
    campaign_id="68c91223fde0aa95caa3dbe4",
    voice_agent_id="68c9105cfde0aa95caa3db64",
    client_id="68c90d626052ee95ac77059d", 
    caller_phone="+919876543210",
    lead_file_path="leads/lead_20251013_135233.json"
)
```

#### Bulk Upload
```python
from crm_upload import bulk_upload_from_directory

results = bulk_upload_from_directory(
    conversations_dir="conversations/",
    leads_dir="leads/",
    campaign_id="68c91223fde0aa95caa3dbe4",
    voice_agent_id="68c9105cfde0aa95caa3db64",
    client_id="68c90d626052ee95ac77059d"
)
# Returns: {"success": 5, "failed": 1, "total": 6}
```

## Testing

Run the test suite to verify functionality:

```bash
python test_crm_upload.py
```

This will test:
- Data format conversion 
- Payload structure validation
- File upload simulation (API calls commented out by default)

To test actual API calls:
1. Uncomment the API call lines in `test_crm_upload.py`
2. Ensure you have valid campaign/agent/client IDs
3. Run the test script

## Integration with Transcript Logger

The transcript logger (`transcript_logger.py`) now includes automatic CRM upload:

1. When a conversation session ends, `save_conversation_session()` is called
2. If `CRM_AUTO_UPLOAD=true` and required config is set, it automatically uploads to CRM
3. It looks for associated lead files if `lead_generated=true` in the session
4. Success/failure is logged

## Data Mapping

### Transcript Session → API Transcription
- `session_id` → `session_id`
- `start_time` → `start_time` 
- `end_time` → `end_time`
- `duration_seconds` → `duration_seconds`
- `items` (filtered for user/assistant) → `conversation_items`
- `lead_generated` → `lead_generated`
- `metadata` → `metadata`

### Lead File → API Lead
- `name` → `name`
- `email` → `email` 
- `company` → `company`
- `interest` → `interest`
- `phone` → `phone`
- `job_title` → `job_title`
- `budget` → `budget`
- `timeline` → `timeline`
- `timestamp` → `timestamp`
- `source` → `source`
- `status` → `status`

## Error Handling

- API errors are logged but don't stop the conversation flow
- File upload failures fall back gracefully
- Invalid data is logged with specific error messages
- Network timeouts use 30-second timeout

## Dependencies

Required packages:
- `requests` - for HTTP API calls
- Standard library: `json`, `os`, `datetime`, `logging`, `pathlib`

No additional dependencies beyond what's already in `requirements.txt`.