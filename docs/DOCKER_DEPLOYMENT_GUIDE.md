# FRIDAY AI: Docker Deployment Guide

This guide covers the complete Docker deployment setup for the FRIDAY AI conversation logging system.

## 🐳 Docker Files Overview

### Core Docker Files

1. **`Dockerfile`** - Multi-stage build with automatic plugin modification
2. **`docker-compose.yml`** - Complete orchestration with optional services
3. **`.dockerignore`** - Optimized build context
4. **`.env.template`** - Environment variables template

### Docker Scripts

1. **`docker_scripts/apply_modifications.py`** - Automatically applies plugin modifications during build
2. **`docker_scripts/verify_modifications.py`** - Verifies modifications were applied correctly

## 🚀 Quick Deployment

### 1. Setup Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your actual API keys
nano .env
```

### 2. Production Deployment

```bash
# Build and start production container
docker-compose up -d friday-ai-agent

# Check logs
docker-compose logs -f friday-ai-agent

# Check health
docker-compose ps
```

### 3. Development Deployment

```bash
# Start development container with hot reload
docker-compose --profile dev up -d friday-ai-dev

# View logs
docker-compose logs -f friday-ai-dev
```

## 📁 Docker Architecture

### Multi-Stage Build

```dockerfile
# Stage 1: Base - Python + dependencies
FROM python:3.10-slim as base

# Stage 2: Development - Full application with modifications
FROM base as development

# Stage 3: Production - Minimal optimized container
FROM base as production
```

### Automatic Plugin Modification

During the Docker build:

1. **Install Plugins**: `pip install livekit-plugins-*`
2. **Apply Modifications**: `python docker_scripts/apply_modifications.py`
3. **Verify**: `python docker_scripts/verify_modifications.py`
4. **Health Check**: Continuous verification

## 🔧 Configuration

### Environment Variables

```bash
# Required
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_secret
GOOGLE_API_KEY=your_google_key
CARTESIA_API_KEY=your_cartesia_key
DEEPGRAM_API_KEY=your_deepgram_key

# Optional
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Automating SIP Trunk & Dispatch creation

If you're provisioning SIP resources from automation or scripts (outside Docker), use the `lk` CLI and parse its JSON output to avoid manual copy/paste. Example (run from project root where `sip-setup/` lives):

```bash
# Create inbound trunk and capture its ID
TRUNK_ID=$(lk sip inbound create --project friday sip-setup/inbound_trunk.json | jq -r '.sip_trunk_id')

# Replace placeholder in dispatch JSON and create the dispatch rule
sed -i "s/REPLACE_WITH_TRUNK_ID/$TRUNK_ID/g" sip-setup/sip_dispatch.json
lk sip dispatch create --project friday sip-setup/sip_dispatch.json
```

This mirrors the canonical quick-start in `README.md` and reduces human error when creating trunks and dispatch rules.

### Volume Mounts

- **`./conversations:/app/conversations`** - Persistent conversation logs
- **`friday-logs:/app/logs`** - Application logs

## 🔍 Health Checks

### Automatic Health Monitoring

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, sys; print('Health check passed' if os.path.isdir('/app/conversations') else 'conversations missing'); sys.exit(0)"
```

### Manual Health Check

```bash
# Check container health
docker inspect friday-ai-agent --format='{{.State.Health.Status}}'

# View health check logs
docker inspect friday-ai-agent --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

## 📊 Service Profiles

### Available Profiles

1. **Default**: Production agent only
2. **`dev`**: Development environment with hot reload
3. **`frontend`**: Include frontend service (future)
4. **`database`**: Include PostgreSQL for advanced logging

### Profile Usage

```bash
# Development
docker-compose --profile dev up -d

# With frontend
docker-compose --profile frontend up -d

# Full stack
docker-compose --profile dev --profile frontend --profile database up -d
```

## 🛠️ Troubleshooting

### Plugin Modification Issues

```bash
# Check if modifications were applied
docker exec friday-ai-agent python docker_scripts/verify_modifications.py

# View plugin modification logs
docker logs friday-ai-agent | grep "FRIDAY AI:"
```

### Conversation Logging Issues

```bash
# Check conversation directory
docker exec friday-ai-agent ls -la conversations/

# Test logging manually: check conversations dir exists
docker exec friday-ai-agent python -c "import os; print('conversations exists:', os.path.isdir('/app/conversations'))"
```

### Container Debugging

```bash
# Enter container shell
docker exec -it friday-ai-agent bash

# Check Python environment
docker exec friday-ai-agent python -c "
import sys
print('Python:', sys.version)
print('Path:', sys.path)
"
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Rebuild with latest changes
docker-compose build friday-ai-agent

# Restart with new image
docker-compose up -d friday-ai-agent
```

### Backup Conversation Logs

```bash
# Backup conversations
docker cp friday-ai-agent:/app/conversations ./backup-conversations-$(date +%Y%m%d)

# Or use volume backup
docker run --rm -v friday_conversations:/data -v $(pwd):/backup alpine tar czf /backup/conversations-backup.tar.gz -C /data .
```

## 🔒 Security Considerations

### API Key Management

- Use Docker secrets for production
- Never commit `.env` file
- Rotate API keys regularly

### Container Security

```bash
# Run as non-root user (add to Dockerfile)
RUN useradd -m -u 1000 friday && chown -R friday:friday /app
USER friday

# Use read-only filesystem
docker run --read-only --tmpfs /tmp friday-ai-agent
```

## 📈 Monitoring and Logs

### Log Aggregation

```bash
# Centralized logging
docker-compose logs -f | tee friday-ai.log

# JSON logs for parsing
docker logs friday-ai-agent --format json
```

### Performance Monitoring

```bash
# Container stats
docker stats friday-ai-agent

# Resource usage
docker exec friday-ai-agent cat /proc/meminfo
docker exec friday-ai-agent cat /proc/loadavg
```

## 🔧 Advanced Configuration

### Custom Plugin Modifications

To add custom modifications:

1. Update `backup_plugin_modifications/`
2. Modify `docker_scripts/apply_modifications.py`
3. Rebuild container

### Production Scaling

```bash
# Scale multiple instances
docker-compose up -d --scale friday-ai-agent=3

# Load balancer configuration
# Add nginx/traefik for load balancing
```

## 🚨 Emergency Procedures

### Rollback to Original Plugins

```bash
# Access backup files
docker exec friday-ai-agent ls /app/original_plugin_backups/

# Manual restoration (if needed)
docker exec friday-ai-agent cp /app/original_plugin_backups/google_llm_original.py /usr/local/lib/python3.10/site-packages/livekit/plugins/google/llm.py
```

### Complete Reset

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker rmi friday-copy_friday-ai-agent

# Clean rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

## 📝 Notes

- All modifications are marked with "FRIDAY AI:" comments
- Health checks ensure modifications are working
- Conversation logs are persisted in `./conversations/`
- Development mode enables hot reload for testing

This Docker setup ensures reliable deployment with automatic plugin modification and comprehensive monitoring!
