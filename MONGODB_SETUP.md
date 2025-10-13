# MongoDB Setup Guide for Friday AI

## Quick Start

### 1. Environment Variables
Create a `.env` file in the project root or set these environment variables:

```bash
# MongoDB Atlas Configuration
MONGODB_URI=mongodb+srv://malayjainttbs_db_user:zJhIUCpEhfah9gLP@cluster0.xhomp4e.mongodb.net/
MONGODB_DATABASE=friday_ai
MONGODB_TIMEOUT=10000

# Feature Toggle
USE_MONGODB=true
```

### 2. Install Dependencies
```bash
pip install pymongo dnspython
```

### 3. Test Connection
```bash
python -c "from db_config import test_connection; print('MongoDB Connected:', test_connection())"
```

### 4. View Data
```bash
python view_mongodb_data.py
```

## Migration Commands

### One-Time Migration (if needed)
```bash
# Migrate existing files to MongoDB
python migrate_to_mongodb.py

# Test the integration
python test_mongodb_integration.py
```

## MongoDB Atlas Access

- **Connection String:** `mongodb+srv://malayjainttbs_db_user:zJhIUCpEhfah9gLP@cluster0.xhomp4e.mongodb.net/`
- **Database:** `friday_ai`
- **Collections:** `leads`, `transcript_events`, `conversation_sessions`

## Local Fallback

If MongoDB is unavailable, the system automatically falls back to local file storage:
- Leads: `leads/lead_YYYYMMDD_HHMMSS.json`
- Conversations: `conversations/transcripts.jsonl`
- Sessions: `conversations/transcript_session_*.json`

## Troubleshooting

### Connection Issues
```bash
# Check MongoDB connection
python -c "from db_config import validate_environment; validate_environment()"
```

### View Logs
```bash
# Check application logs for MongoDB errors
grep -i mongodb logs/application.log
```

### Disable MongoDB (Emergency)
```bash
# Set environment variable to disable MongoDB
export USE_MONGODB=false
# Or create .env file with USE_MONGODB=false
```