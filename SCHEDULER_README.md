# Temporary Upload Scheduler API

This is a temporary testing setup using Uvicorn as a scheduler to test the upload functionality without interfering with the main LiveKit agent.

## 🚀 Quick Start

```bash
# Run the scheduler API
uvicorn scheduler_api:app --host 0.0.0.0 --port 9000 --reload
```

## 📋 Endpoints

### GET `/`
- **Status check** - Returns basic API status
- **Response**: `{"status": "Upload Scheduler API running", "timestamp": "...", "sync_running": false, "last_sync": "..."}`

### GET `/status`
- **Detailed statistics** - Get comprehensive sync statistics
- **Response**: Includes sync status, run counts, success rates, and last sync details

### GET `/force-sync`
- **Manual trigger** - Immediately run the upload sync
- **Response**: `{"message": "Manual sync started in background", "timestamp": "..."}`

### GET `/dry-run`
- **Test mode** - See what would be uploaded without actually uploading
- **Response**: Shows what files would be processed

## 🔄 Automatic Sync

The scheduler automatically runs the upload cron every **5 minutes** when started.

## 📊 Monitoring

- **Logs**: All sync activity is logged to console and `upload_cron.log`
- **Statistics**: Track success rates, run counts, and timing via `/status` endpoint
- **Real-time**: See sync progress in console when using `--reload`

## 🛠️ Configuration

- **Metadata Directory**: `call_metadata/` (pending uploads)
- **Batch Size**: 10 files per sync run
- **Sync Interval**: 5 minutes (automatic)
- **Upload Logic**: Uses `CentralMetadataUploadCron` from `upload_cron.py`

## 🎯 Testing Workflow

1. **Start the scheduler**: `uvicorn scheduler_api:app --host 0.0.0.0 --port 9000 --reload`
2. **Check status**: Visit `http://localhost:9000/status`
3. **Test dry-run**: Visit `http://localhost:9000/dry-run`
4. **Trigger manual sync**: Visit `http://localhost:9000/force-sync`
5. **Monitor logs**: Watch console output for upload progress

## 🔄 Future Migration

When ready for production:
- Replace `asyncio.sleep()` loop with actual cron job
- Move to systemd timer or scheduled task
- Keep the core upload logic in `upload_cron.py`

## 📝 Notes

- **Non-blocking**: Runs separately from LiveKit agent
- **Easy iteration**: Restart uvicorn to apply code changes
- **Production-ready logic**: Uses the same upload code as cron jobs