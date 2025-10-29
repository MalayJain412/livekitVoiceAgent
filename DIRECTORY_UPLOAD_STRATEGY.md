# Directory-Based Upload Strategy - Simple & Reliable

## 🎯 Overview

This document outlines the **Directory-Based Upload Strategy** for the Friday AI Voice Bot system. This approach uses a **single cron job** that scans existing file directories and uploads files directly to the CRM APIs, eliminating the need for complex queueing systems.

## 🚨 Problem Statement

**Current Issues:**
- Upload logic in finally block interrupted by LiveKit process termination
- User hangups bypass upload process entirely due to immediate room deletion
- Egress files not ready when upload attempted (timing issues)
- Process termination prevents upload completion
- No retry mechanism for failed uploads

**Impact:**
- Recordings not uploaded to storage
- Call data not synchronized with CRM
- Loss of valuable conversation analytics
- Incomplete lead management workflow

## 🔄 Solution Architecture

### Core Concept
**Simple directory scanning**: Single cron job scans conversation/recording/lead files → Uploads recordings first → Uses recording URL for call data upload

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CALL PHASE    │    │  DIRECTORY      │    │  UPLOAD PHASE   │
│                 │    │  SCANNING       │    │                 │
│ 1. Record call  │───▶│ 4. Scan files   │───▶│ 7. Upload .ogg  │
│ 2. Save logs    │    │ 5. Match sets   │    │ 8. Get URL      │
│ 3. Save leads   │    │ 6. Process batch│    │ 9. Upload data  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
      LiveKit Agent        Single Cron Job        Two-Step Upload
    (Real-time process)   (Directory scanner)   (File → URL → Data)
```

## 📁 Current Directory Structure

The system already creates these directories during calls:

```
xeny-livekit-voicebot/
├── recordings/                    # Audio files (.ogg) from egress
│   ├── number-_918655048643-1761635651.ogg
│   ├── number-_918655066243-1761720502.ogg
│   └── ...
├── conversations/                 # Transcript session files (.json)
│   ├── transcript_session_2025-10-29T06-49-07.351452.json
│   ├── transcript_session_2025-10-29T07-23-03.616272.json
│   └── ...
├── leads/                        # Lead files (.json) - when generated
│   ├── leads_session_2025-10-29T06-49-07.351452.json
│   ├── lead_20251013_135233.json
│   └── ...
└── upload_cron.py               # NEW: Single cron script
```

## 🔍 File Matching Strategy

### How Files Are Related
```python
# Example file set for a single call:
recording_file = "recordings/number-_918655066243-1761720502.ogg"
transcript_file = "conversations/transcript_session_2025-10-29T06-49-07.351452.json"
lead_file = "leads/leads_session_2025-10-29T06-49-07.351452.json"  # optional

# Match by timestamp correlation (within 5-minute window)
# OR by session_id extracted from transcript content
```

### File Processing Priority
1. **Primary**: MongoDB-formatted conversation files (transcript_session_*.json)
2. **Secondary**: Recording files (.ogg) in recordings/
3. **Optional**: Lead files in leads/ directory

## 🗂️ Upload Workflow

### Step 1: File Upload to Storage API
```bash
POST https://devcrm.xeny.ai/apis/api/public/upload
Content-Type: multipart/form-data

# Upload recording file
file: recordings/number-_918655066243-1761720502.ogg
```

**Response:**
```json
{
    "success": true,
    "data": {
        "filename": "1761723567342.ogg",
        "originalName": "number-_918655048643-1761635651.ogg",
        "size": 1406083,
        "url": "http://devcrm.xeny.ai/apis/uploads/recordings/1761723567342.ogg",
        "relativeUrl": "/uploads/recordings/1761723567342.ogg"
    }
}
```

### Step 2: Call Data Upload with Recording URL
```bash
POST https://devcrm.xeny.ai/apis/api/public/call-data
Content-Type: application/json
```

**Payload Structure:**
```json
{
    "campaignId": "68c91223fde0aa95caa3dbe4",
    "voiceAgentId": "68c9105cfde0aa95caa3db64", 
    "client": "68c90d626052ee95ac77059d",
    "callDetails": {
        "callId": "CALL-20251029-121530-66243",
        "direction": "inbound",
        "startTime": "2025-10-29T12:15:30.123Z",
        "endTime": "2025-10-29T12:16:05.456Z",
        "duration": 35,
        "status": "completed",
        "callerNumber": "+918655066243",
        "recordingUrl": "http://devcrm.xeny.ai/apis/uploads/recordings/1761723567342.ogg",
        "recordingDuration": 35,
        "recordingSize": 1406083
    },
    "caller": {
        "phoneNumber": "+918655066243"
    },
    "transcription": {
        "session_id": "session_20251029_064824_2e0aa754",
        "start_time": "2025-10-29T12:15:30.123Z",
        "end_time": "2025-10-29T12:16:05.456Z",
        "duration_seconds": 35,
        "total_items": 12,
        "conversation_items": [
            {
                "role": "assistant",
                "content": "Hello! This is Friday from Xeny AI...",
                "timestamp": "2025-10-29T12:15:32.123Z",
                "source": "voice_agent",
                "transcript_confidence": null
            }
        ],
        "lead_generated": true,
        "metadata": {
            "auto_saved": true
        }
    },
    "lead": {
        "name": "Malay Jain",
        "email": "malay@example.com",
        "company": "Tech Corp",
        "interest": "AI solutions"
    }
}
```

## ⚙️ Implementation: upload_cron.py

### Core Functions

```python
class DirectoryUploadCron:
    """Single cron job that scans directories and uploads files"""
    
    def __init__(self):
        self.conversations_dir = "conversations"
        self.recordings_dir = "recordings"
        self.leads_dir = "leads"
        self.processed_dir = "processed_uploads"  # Track completed uploads
        
    def scan_and_upload(self):
        """Main cron function - scans directories and uploads"""
        
    def get_unprocessed_conversations(self):
        """Get conversation files not yet uploaded"""
        
    def find_matching_recording(self, conversation_file):
        """Find .ogg recording that matches conversation timestamp"""
        
    def find_matching_lead(self, conversation_file):
        """Find lead file that matches conversation session"""
        
    def upload_recording_file(self, recording_path):
        """Upload .ogg file to storage API and return URL"""
        
    def upload_call_data_set(self, conversation_file, recording_url, lead_file):
        """Upload complete call data to CRM API"""
        
    def mark_as_processed(self, conversation_file):
        """Move/mark file as processed to avoid re-upload"""
```

### Key Implementation Details

**File Matching Logic:**
```python
def find_matching_recording(self, conversation_path):
    """Find recording that matches conversation by timestamp proximity"""
    
    # Extract conversation timestamp
    conversation_time = self.extract_timestamp_from_conversation(conversation_path)
    
    # Look for recordings within 5-minute window
    for recording_file in os.listdir(self.recordings_dir):
        if recording_file.endswith('.ogg'):
            # Parse recording timestamp from filename or file stats
            recording_time = self.extract_timestamp_from_recording(recording_file)
            
            # Match if within 5-minute window
            if abs((conversation_time - recording_time).total_seconds()) < 300:
                return os.path.join(self.recordings_dir, recording_file)
    
    return None
```

**Upload State Tracking:**
```python
def mark_as_processed(self, conversation_file):
    """Track processed files to avoid re-upload"""
    
    # Create processed_uploads directory structure
    processed_path = os.path.join("processed_uploads", 
                                  os.path.basename(conversation_file))
    
    # Option 1: Move file
    shutil.move(conversation_file, processed_path)
    
    # Option 2: Create marker file
    with open(processed_path + ".uploaded", 'w') as f:
        f.write(json.dumps({
            "uploaded_at": datetime.utcnow().isoformat(),
            "original_path": conversation_file
        }))
```

## ⏰ Cron Job Configuration

### Linux/Unix Cron Setup
```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/xeny-livekit-voicebot && python upload_cron.py >> upload_cron.log 2>&1

# Run every 10 minutes during business hours
*/10 9-17 * * 1-5 cd /path/to/xeny-livekit-voicebot && python upload_cron.py >> upload_cron.log 2>&1

# Run once per hour (less aggressive)
0 * * * * cd /path/to/xeny-livekit-voicebot && python upload_cron.py >> upload_cron.log 2>&1
```

### Windows Task Scheduler
```powershell
# Create scheduled task for Windows
schtasks /create /tn "VoiceBotDirectoryUpload" /tr "python C:\path\to\upload_cron.py" /sc minute /mo 5 /ru SYSTEM
```

## 🔄 Process Flow Details

### Phase 1: Directory Scanning (Every 5 minutes)

1. **Scan Conversations**: Look for `transcript_session_*.json` files not yet processed
2. **File Validation**: Ensure files are complete and readable
3. **Match Recording**: Find corresponding `.ogg` file by timestamp correlation
4. **Match Lead**: Find corresponding lead file (if exists)
5. **Batch Processing**: Process files in sets (conversation + recording + lead)

### Phase 2: Upload Processing

1. **Recording Upload**:
   - Upload `.ogg` file to `/apis/api/public/upload`
   - Extract recording URL from response
   - Store URL for call data upload

2. **Call Data Upload**:
   - Format conversation data according to API schema
   - Include recording URL in `callDetails.recordingUrl`
   - Upload to `/apis/api/public/call-data`

3. **State Tracking**:
   - Mark files as processed to avoid re-upload
   - Log success/failure for monitoring

### Phase 3: Error Handling

1. **File Matching Failures**: Log when recordings can't be matched to conversations
2. **Upload Failures**: Retry with exponential backoff (1min, 5min, 15min)
3. **Partial Failures**: If recording uploads but call data fails, retry call data only
4. **Monitoring**: Comprehensive logging for troubleshooting

## 🗂️ Upload State Management

### Processed Files Tracking
```
processed_uploads/
├── transcript_session_2025-10-29T06-49-07.351452.json.uploaded
├── transcript_session_2025-10-29T07-23-03.616272.json.uploaded
└── ...

# Each .uploaded file contains:
{
    "uploaded_at": "2025-10-29T12:30:15.123Z",
    "original_path": "conversations/transcript_session_2025-10-29T06-49-07.351452.json",
    "recording_uploaded": true,
    "recording_url": "http://devcrm.xeny.ai/apis/uploads/recordings/1761723567342.ogg",
    "call_data_uploaded": true,
    "lead_uploaded": true,
    "upload_attempts": 1
}
```

## 📊 Monitoring & Logging

### Log Output Example
```
2025-10-29 12:30:00 [INFO] Directory scan started
2025-10-29 12:30:01 [INFO] Found 3 unprocessed conversation files
2025-10-29 12:30:01 [INFO] Processing: transcript_session_2025-10-29T07-23-03.616272.json
2025-10-29 12:30:02 [INFO] Matched recording: number-_918655066243-1761720502.ogg
2025-10-29 12:30:02 [INFO] Found lead file: leads_session_2025-10-29T07-23-03.616272.json
2025-10-29 12:30:05 [INFO] Recording uploaded: 245KB → http://devcrm.xeny.ai/apis/uploads/recordings/1761723567342.ogg
2025-10-29 12:30:07 [INFO] Call data uploaded successfully: CALL-20251029-072303-66243
2025-10-29 12:30:07 [INFO] File marked as processed
2025-10-29 12:30:10 [INFO] Directory scan completed: 3 processed, 0 failed
```

### Daily Summary Reporting
```python
def generate_daily_summary():
    """Generate daily upload statistics"""
    return {
        "date": "2025-10-29",
        "files_processed": 45,
        "recordings_uploaded": 43,
        "call_data_uploaded": 45,
        "leads_uploaded": 12,
        "failed_uploads": 2,
        "success_rate": "95.6%",
        "total_data_mb": 1250
    }
```

## 🚀 Benefits of Directory-Based Approach

1. **Simplicity**: Single script, no complex queue management
2. **Reliability**: Uses existing file system as "queue"
3. **Resumable**: Failed uploads automatically retried on next run
4. **Transparent**: Easy to see what files need processing
5. **Maintenance**: Simple to debug and modify
6. **Scalable**: Can process large batches efficiently
7. **Fault-Tolerant**: Survives system restarts without data loss

## 🔧 Configuration

### Environment Variables
```bash
# CRM API Configuration
CRM_UPLOAD_URL="https://devcrm.xeny.ai/apis/api/public/upload"
CRM_CALL_DATA_URL="https://devcrm.xeny.ai/apis/api/public/call-data"

# Default Campaign Settings
DEFAULT_CAMPAIGN_ID="68c91223fde0aa95caa3dbe4"
DEFAULT_VOICE_AGENT_ID="68c9105cfde0aa95caa3db64"
DEFAULT_CLIENT_ID="68c90d626052ee95ac77059d"

# Upload Configuration
UPLOAD_BATCH_SIZE=10
UPLOAD_RETRY_ATTEMPTS=3
UPLOAD_TIMEOUT_SECONDS=30

# Directory Configuration
CONVERSATIONS_DIR="conversations"
RECORDINGS_DIR="recordings"
LEADS_DIR="leads"
PROCESSED_DIR="processed_uploads"
```

## 📝 Implementation Checklist

- [ ] Create `upload_cron.py` with directory scanning logic
- [ ] Add recording file upload function to `crm_upload.py`
- [ ] Implement file matching algorithms (timestamp-based)
- [ ] Add upload state tracking (processed files)
- [ ] Set up cron job for regular execution
- [ ] Add comprehensive logging and monitoring
- [ ] Test with existing conversation/recording files
- [ ] Deploy and monitor in production

## 🔮 Future Enhancements

1. **Web Dashboard**: View upload status and statistics
2. **Manual Trigger**: Web interface to manually trigger uploads
3. **Selective Processing**: Upload specific date ranges or files
4. **Performance Optimization**: Parallel uploads for large batches
5. **Advanced Matching**: Use conversation content to match recordings
6. **Backup Strategy**: Archive processed files to cloud storage

---

**This directory-based approach transforms upload from a complex scheduling system to a simple, reliable cron job that processes files as they appear, with full error recovery and monitoring capabilities.**