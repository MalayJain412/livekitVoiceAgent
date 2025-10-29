# Scheduled Upload Strategy - Complete Implementation Plan

## 🎯 Overview

This document outlines the **Scheduled Upload Strategy** for the Friday AI Voice Bot system, designed to solve the CRM upload reliability issues by completely separating upload processing from the real-time call lifecycle.

## 🚨 Problem Statement

**Current Issues:**
- Upload logic in `finally` block interrupted by LiveKit process termination
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
**Decouple upload from call lifecycle**: Collect metadata during call → Queue for processing → Separate scheduler handles uploads

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CALL PHASE    │    │   QUEUE PHASE    │    │  UPLOAD PHASE   │
│                 │    │                  │    │                 │
│ 1. Record call  │───▶│ 4. Store metadata│───▶│ 7. Process queue│
│ 2. Save logs    │    │ 5. File paths    │    │ 8. Upload files │
│ 3. Generate     │    │ 6. Queue entry   │    │ 9. Update CRM   │
│    metadata     │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
      LiveKit Agent           JSON Queue              Cron/Scheduler
    (Real-time process)    (Persistent storage)     (Background process)
```

## 📁 File Structure Implementation

```
xeny-livekit-voicebot/
├── recordings/                    # Audio files (.ogg)
├── conversations/                 # Transcript files (.json)
├── leads/                        # Lead data files (.json)
├── upload_queue/                 # NEW: Upload queue system
│   ├── pending/                  # Items waiting for upload
│   ├── processing/               # Items currently being uploaded
│   ├── completed/                # Successfully uploaded items
│   ├── failed/                   # Failed upload attempts
│   └── dead_letter/              # Permanent failures after max retries
├── upload_scheduler.py           # NEW: Background upload processor
├── queue_manager.py             # NEW: Queue management utilities
├── metadata_collector.py        # NEW: Metadata collection during calls
└── docs/
    └── SCHEDULED_UPLOAD_STRATEGY.md  # This document
```

## 🗂️ Metadata Schema

### Queue Item Structure
Each upload queue item is a JSON file with the following structure:

```json
{
  "call_id": "CALL-20251029-121530-66243",
  "session_id": "session_20251029_064824_2e0aa754",
  "timestamp": "2025-10-29T12:15:30.123Z",
  "dialed_number": "+918655066243",
  "persona_name": "Malay Jain",
  "campaign_info": {
    "campaign_id": "cm123456",
    "voice_agent_id": "va789012",
    "client_id": "cl345678"
  },
  "files": {
    "recording": {
      "path": "recordings/number-_918655066243-1761720502.ogg",
      "filename": "number-_918655066243-1761720502.ogg",
      "size": 245760,
      "egress_id": "EG_JXhquANAGAvX",
      "duration_estimate": 35
    },
    "transcript": {
      "path": "conversations/transcript_session_2025-10-29T06-49-07.351452.json",
      "filename": "transcript_session_2025-10-29T06-49-07.351452.json",
      "size": 2048
    },
    "leads": {
      "path": "leads/leads_session_2025-10-29T06-49-07.351452.json",
      "filename": "leads_session_2025-10-29T06-49-07.351452.json",
      "size": 512,
      "lead_count": 1
    }
  },
  "call_metrics": {
    "start_time": "2025-10-29T12:15:30.123Z",
    "end_time": "2025-10-29T12:16:05.456Z",
    "duration_seconds": 35,
    "hangup_reason": "user_requested"
  },
  "upload_status": {
    "status": "pending",
    "created_at": "2025-10-29T12:16:05.500Z",
    "attempts": 0,
    "last_attempt": null,
    "error_message": null,
    "upload_results": {
      "recording_url": null,
      "transcript_uploaded": false,
      "leads_uploaded": false,
      "crm_uploaded": false
    }
  }
}
```

## ⚙️ Implementation Components

### 1. Metadata Collector (`metadata_collector.py`)

**Purpose**: Collects all call metadata during LiveKit session end
**Integration Point**: Called from `cagent.py` before hangup

```python
class MetadataCollector:
    """Collects call metadata during LiveKit session"""
    
    async def collect_call_metadata(self, session_manager, egress_info, persona_config)
    async def save_to_queue(self, metadata, queue_path="upload_queue/pending")
    def generate_call_id(self, dialed_number)
    def estimate_duration(self, file_size_bytes)
    def get_file_info(self, file_path)
    def extract_campaign_info(self, persona_config)
```

**Key Responsibilities:**
- Extract file paths from SessionManager
- Calculate file sizes and estimates
- Generate unique call IDs
- Create queue metadata structure
- Save to pending queue

### 2. Queue Manager (`queue_manager.py`)

**Purpose**: Manages upload queue operations and state transitions

```python
class UploadQueueManager:
    """Manages upload queue operations"""
    
    def __init__(self, queue_base_path="upload_queue")
    def add_to_queue(self, metadata)
    def get_pending_items(self, limit=10)
    def move_to_processing(self, item_id)
    def mark_completed(self, item_id, upload_results)
    def mark_failed(self, item_id, error_message)
    def retry_failed_items(self, max_retries=3)
    def cleanup_old_items(self, days_old=7)
    def get_queue_stats(self)
```

**Key Responsibilities:**
- Queue state management (pending → processing → completed/failed)
- Atomic file operations to prevent corruption
- Retry logic for failed items
- Queue cleanup and maintenance
- Statistics and monitoring

### 3. Upload Scheduler (`upload_scheduler.py`)

**Purpose**: Background process that processes queued uploads

```python
class UploadScheduler:
    """Background process that handles queued uploads"""
    
    def __init__(self, queue_manager, upload_config)
    async def process_queue_continuously(self, interval_seconds=180)
    async def upload_single_item(self, metadata)
    async def upload_recording(self, file_path, metadata)
    async def upload_transcript(self, file_path, metadata)
    async def upload_leads(self, file_path, metadata)
    async def upload_to_crm(self, metadata, upload_results)
    def validate_files(self, metadata)
    def cleanup_old_completed_items(self)
```

**Key Responsibilities:**
- Continuous queue processing
- File validation before upload
- Sequential upload process (recording → transcript → leads → CRM)
- Error handling and retry logic
- Upload result tracking

## 🔄 Process Flow Details

### Phase 1: During Call (Real-time in cagent.py)

1. **Recording Starts**: Egress creates `.ogg` file with `egress_id`
2. **Session Tracking**: SessionManager tracks conversation in real-time
3. **Lead Generation**: Tools create lead files in `leads/` directory if applicable
4. **Call End Detection**: Either agent tool `end_call` or user hangup
5. **Metadata Collection**: `MetadataCollector.collect_call_metadata()`
   - Extract recording file path from egress
   - Get transcript file path from SessionManager
   - Check for lead files in session
   - Generate call metadata structure
6. **Queue Entry**: Save metadata JSON to `upload_queue/pending/{call_id}.json`
7. **Call Termination**: LiveKit process terminates cleanly without upload dependency

### Phase 2: Queue Processing (Background Scheduler)

1. **Scheduler Execution**: 
   - Cron job or built-in scheduler runs `upload_scheduler.py`
   - Default interval: Every 3 minutes
2. **Queue Scan**: Check `upload_queue/pending/` for new items
3. **Item Processing**:
   - Move item to `upload_queue/processing/`
   - Validate all referenced files exist and are readable
   - Check file sizes match metadata expectations
4. **Upload Sequence**:
   - **Step 1**: Upload recording file to storage API
   - **Step 2**: Upload transcript file (if exists)
   - **Step 3**: Upload lead files (if exists)
   - **Step 4**: Upload complete call data to CRM API
5. **Result Handling**:
   - **Success**: Move to `upload_queue/completed/`
   - **Failure**: Move to `upload_queue/failed/` with error details

### Phase 3: Error Handling & Recovery

1. **Failed Item Detection**: Items in `upload_queue/failed/`
2. **Retry Logic**: 
   - Exponential backoff: 1min, 5min, 15min, 1hour
   - Maximum 3 retry attempts per item
3. **Permanent Failure**: 
   - After max retries, move to `upload_queue/dead_letter/`
   - Alert administrators for manual intervention
4. **Monitoring**: 
   - Log all upload attempts with detailed error messages
   - Track success/failure rates
5. **Cleanup**: 
   - Remove completed items older than 7 days
   - Archive failed items for analysis

## ⏰ Scheduling Implementation Options

### Option A: Cron Job (Linux/Unix - Recommended for Production)

```bash
# Add to crontab (crontab -e)
# Run every 3 minutes
*/3 * * * * cd /path/to/xeny-livekit-voicebot && python upload_scheduler.py >> upload_scheduler.log 2>&1

# Alternative: Run every minute during business hours
* 9-17 * * 1-5 cd /path/to/xeny-livekit-voicebot && python upload_scheduler.py >> upload_scheduler.log 2>&1
```

### Option B: Windows Task Scheduler

```powershell
# Create scheduled task for Windows
schtasks /create /tn "VoiceBotUpload" /tr "python C:\path\to\upload_scheduler.py" /sc minute /mo 3 /ru SYSTEM
```

### Option C: Python APScheduler (Built-in - Recommended for Development)

```python
# In upload_scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_queue, 'interval', minutes=3)
    scheduler.start()
    
    # Keep the scheduler running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logging.info("Scheduler stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Monitoring & Observability

### Queue Metrics Dashboard

```python
# Example monitoring output
{
  "queue_stats": {
    "pending": 5,
    "processing": 2,
    "completed_today": 127,
    "failed_today": 3,
    "success_rate": "97.7%"
  },
  "upload_performance": {
    "avg_processing_time_seconds": 45,
    "recordings_uploaded_mb": 1250,
    "api_response_time_ms": 850
  },
  "error_summary": {
    "network_timeouts": 2,
    "file_not_found": 1,
    "api_rate_limits": 0
  }
}
```

### Log Structure

```
2025-10-29 12:15:30 [INFO] Queue scan started: 5 pending items
2025-10-29 12:15:31 [INFO] Processing item: CALL-20251029-121530-66243
2025-10-29 12:15:31 [INFO] Files validated: recording=OK, transcript=OK, leads=NOT_FOUND
2025-10-29 12:15:35 [INFO] Recording uploaded: 245KB in 3.2s
2025-10-29 12:15:36 [INFO] Transcript uploaded: 2KB in 0.8s
2025-10-29 12:15:38 [INFO] CRM upload completed: call_data_id=CD_xyz123
2025-10-29 12:15:38 [INFO] Item completed: CALL-20251029-121530-66243
```

## 🔒 Error Recovery Strategies

### Temporary Failures (Retry with Backoff)
- Network timeouts
- API rate limits
- Temporary file locks
- Service unavailability

### Permanent Failures (Move to Dead Letter)
- Missing files (file not found after 24 hours)
- Invalid metadata format
- Authentication failures
- Corrupted files

### Partial Failures (Resume from Checkpoint)
- Recording uploaded, transcript failed → Resume from transcript
- Files uploaded, CRM failed → Retry CRM only
- Maintain upload state to avoid duplicate uploads

## 🚀 Benefits of This Approach

1. **Robust**: No dependency on LiveKit process lifecycle
2. **Scalable**: Can handle high call volumes with queue batching
3. **Reliable**: Retry mechanisms and comprehensive error recovery
4. **Monitorable**: Clear visibility into upload pipeline status
5. **Maintainable**: Separate concerns, easy to debug and modify
6. **Flexible**: Can adjust scheduling frequency based on load
7. **Fault-Tolerant**: Survives system restarts and network issues

## 🔧 Integration Points

### Modification to cagent.py

```python
# At the end of call processing, before hangup
from metadata_collector import MetadataCollector

# Create metadata and queue for upload
collector = MetadataCollector()
metadata = await collector.collect_call_metadata(
    session_manager=session_manager,
    egress_info=egress_info,
    persona_config=full_config
)
await collector.save_to_queue(metadata)
logging.info(f"Call metadata queued for upload: {metadata['call_id']}")

# Proceed with hangup - upload happens independently
await hangup_call()
```

### New Configuration Options

```python
# In config.py
UPLOAD_QUEUE_CONFIG = {
    "enabled": True,
    "queue_path": "upload_queue",
    "scheduler_interval_minutes": 3,
    "max_retries": 3,
    "cleanup_days": 7,
    "batch_size": 10
}

UPLOAD_ENDPOINTS = {
    "storage_api": "https://devcrm.xeny.ai/apis/api/public/upload",
    "crm_api": "https://devcrm.xeny.ai/apis/api/call-data"
}
```

## 📝 Implementation Checklist

- [ ] Create `upload_queue/` directory structure
- [ ] Implement `metadata_collector.py`
- [ ] Implement `queue_manager.py`
- [ ] Implement `upload_scheduler.py`
- [ ] Modify `cagent.py` to use metadata collector
- [ ] Set up cron job or scheduler
- [ ] Add monitoring and logging
- [ ] Test with sample call data
- [ ] Deploy and monitor in production

## 🔮 Future Enhancements

1. **Web Dashboard**: Real-time queue monitoring interface
2. **Webhook Notifications**: Alert on upload failures
3. **Batch Processing**: Group multiple uploads for efficiency
4. **Priority Queues**: High-priority calls uploaded first
5. **Distributed Processing**: Multiple worker processes
6. **Data Compression**: Reduce upload bandwidth usage

---

**This strategy transforms upload from a fragile in-process operation to a robust, scalable background service that can handle any volume of calls with complete reliability.**