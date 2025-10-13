# MongoDB Migration Guide for Friday AI

This guide covers the complete migration from local file storage to MongoDB for leads and conversations in the Friday AI system.

## Overview

The migration replaces:
- **Lead storage**: From individual JSON files (`leads/lead_*.json`) to MongoDB `leads` collection
- **Conversation logging**: From JSONL file (`conversations/transcripts.jsonl`) to MongoDB `transcript_events` collection  
- **Session storage**: From JSON files (`conversations/transcript_session_*.json`) to MongoDB `conversation_sessions` collection

## Prerequisites

### 1. MongoDB Server Setup

#### Option A: Local MongoDB Installation
```powershell
# Download and install MongoDB Community Edition
# Start MongoDB service
net start MongoDB

# Verify MongoDB is running
mongo --eval "db.adminCommand('listCollections')"
```

#### Option B: MongoDB Atlas (Cloud)
1. Create account at [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a new cluster
3. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/friday_ai`

#### Option C: Docker MongoDB
```powershell
# Run MongoDB in Docker
docker run -d -p 27017:27017 --name friday-mongo -e MONGO_INITDB_DATABASE=friday_ai mongo:latest

# Verify container is running
docker ps
```

### 2. Environment Configuration

Create or update environment variables:
```powershell
# Set MongoDB connection details
$env:MONGODB_URI = "mongodb://localhost:27017/"  # or your MongoDB Atlas URI
$env:MONGODB_DATABASE = "friday_ai"
$env:USE_MONGODB = "true"
```

For production, add to `.env` file:
```env
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=friday_ai
USE_MONGODB=true
```

## Installation Steps

### 1. Install Dependencies
```powershell
# Install MongoDB Python driver
pip install -r requirements.txt

# Or install specific packages
pip install pymongo dnspython
```

### 2. Test MongoDB Connection
```powershell
# Test the MongoDB integration
python test_mongodb_integration.py --install-deps
```

### 3. Run Migration

#### Dry Run (Recommended First)
```powershell
# See what would be migrated without making changes
python migrate_to_mongodb.py --dry-run
```

#### Full Migration
```powershell
# Migrate all data
python migrate_to_mongodb.py

# Or migrate specific data types
python migrate_to_mongodb.py --leads-only
python migrate_to_mongodb.py --conversations-only
```

### 4. Verify Migration
```powershell
# Test all MongoDB functionality
python test_mongodb_integration.py

# Check data in MongoDB
python -c "
from mongodb_queries import get_lead_stats, get_conversation_stats
print('Leads:', get_lead_stats())
print('Conversations:', get_conversation_stats())
"
```

## Database Schema

### Collections Created

1. **leads** - Lead information
   - Unique index on `email`
   - Indexes on `timestamp`, `status`, `company`, `interest`

2. **transcript_events** - Real-time conversation events
   - Indexes on `timestamp`, `session_id`, `role`

3. **conversation_sessions** - Complete conversation sessions
   - Unique index on `session_id`
   - Indexes on `start_time`, `lead_generated`, `lead_id`

### Data Transformation

**Leads Migration:**
- Preserves all existing fields
- Adds `created_at` and `updated_at` timestamps
- Converts string timestamps to DateTime objects

**Conversation Migration:**
- Groups transcript events by session using timestamps
- Preserves complete session data structure
- Links sessions to generated leads

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `MONGODB_DATABASE` | `friday_ai` | Database name |
| `MONGODB_TIMEOUT` | `5000` | Connection timeout (ms) |
| `USE_MONGODB` | `true` | Enable/disable MongoDB usage |

### Fallback Behavior

The system includes automatic fallback:
- If MongoDB is unavailable, data saves to local files
- Existing file-based operations continue to work
- No data loss during transition period

## Usage Examples

### Query Leads
```python
from mongodb_queries import LeadQueries

# Get recent leads
recent_leads = LeadQueries.get_recent_leads(days=7)

# Search leads
results = LeadQueries.search_leads("triotech")

# Get lead statistics
stats = LeadQueries.get_leads_stats()
```

### Query Conversations
```python
from mongodb_queries import ConversationQueries

# Get sessions with leads generated
lead_sessions = ConversationQueries.get_sessions_with_leads()

# Get conversation statistics
stats = ConversationQueries.get_conversation_stats()
```

### Generate Reports
```python
from mongodb_queries import generate_report

# Weekly summary
weekly_report = generate_report("weekly")

# Daily report
daily_report = generate_report("daily")
```

## Monitoring and Management

### Check System Status
```python
from db_config import validate_environment, test_connection

# Validate configuration
valid = validate_environment()

# Test connection
connected = test_connection()
```

### Performance Monitoring
```python
from mongodb_queries import get_lead_stats, get_conversation_stats

# Monitor lead generation
lead_stats = get_lead_stats()
print(f"Total leads: {lead_stats['total_leads']}")
print(f"Recent leads (7d): {lead_stats['recent_leads_7_days']}")

# Monitor conversation quality
conv_stats = get_conversation_stats()
print(f"Lead conversion rate: {conv_stats['lead_conversion_rate']:.1f}%")
```

## Troubleshooting

### Connection Issues

**Problem**: `ConnectionFailure` or timeout errors
```powershell
# Check MongoDB status
mongo --eval "db.runCommand('ping')"

# Verify network connectivity
ping localhost  # for local MongoDB
```

**Solution**: 
- Ensure MongoDB service is running
- Check firewall settings
- Verify connection string format

### Migration Issues

**Problem**: Duplicate key errors during migration
```
DuplicateKeyError: E11000 duplicate key error
```

**Solution**: 
- Run migration script multiple times (it skips existing records)
- Or clean duplicates before migration

**Problem**: Import errors
```
ImportError: No module named 'pymongo'
```

**Solution**:
```powershell
pip install pymongo dnspython
```

### Data Validation

**Check data integrity**:
```python
# Compare file vs MongoDB counts
import os
from mongodb_queries import get_lead_stats

file_count = len(os.listdir("leads"))
db_stats = get_lead_stats()
print(f"Files: {file_count}, MongoDB: {db_stats['total_leads']}")
```

## Backup and Recovery

### Backup MongoDB Data
```powershell
# Create backup
mongodump --db friday_ai --out backup/

# Restore backup
mongorestore --db friday_ai backup/friday_ai/
```

### Export to JSON
```python
from mongodb_queries import LeadQueries
import json

# Export all leads
leads = LeadQueries.get_recent_leads(days=999)
with open("leads_backup.json", "w") as f:
    json.dump(leads, f, default=str, indent=2)
```

## Production Deployment

### Security Considerations
1. **Authentication**: Enable MongoDB authentication
2. **Network Security**: Use connection encryption (TLS/SSL)
3. **Access Control**: Create dedicated database user with minimal permissions
4. **Environment Variables**: Store credentials securely

### Performance Optimization
1. **Indexes**: All necessary indexes are created automatically
2. **Connection Pooling**: Configured in `db_config.py`
3. **Timeouts**: Adjust `MONGODB_TIMEOUT` based on network latency

### Monitoring
1. **Health Checks**: Use `validate_environment()` in health endpoints
2. **Metrics**: Track lead generation and conversation metrics
3. **Alerts**: Monitor connection failures and performance issues

## Next Steps

After successful migration:

1. **Update cagent.py** to use session management:
   ```python
   from transcript_logger import generate_session_id, save_conversation_session
   
   # At session start
   session_id = generate_session_id()
   
   # At session end
   save_conversation_session(session_items)
   ```

2. **Add reporting dashboard** using `mongodb_queries.py` functions

3. **Set up monitoring** for lead generation and conversation quality

4. **Consider archiving** old local files after successful migration validation