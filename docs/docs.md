# Friday AI Telephony Setup Documentation

## Overview

Friday AI integrates telephony capabilities through LiveKit's SIP gateway, enabling voice calls from SIP clients (e.g., Zoiper) to connect directly to the AI voice assistant. This setup allows inbound phone calls to be bridged into LiveKit rooms where the voice bot operates, facilitating real-time audio exchange between callers and the AI.

### Key Components
- **LiveKit Server**: Handles real-time communication and room management.
- **LiveKit SIP Bridge**: Acts as the SIP gateway, registering SIP users and bridging calls to LiveKit rooms.
- **Redis**: Message bus for PSRPC communication between services.
- **Voice Bot (Friday AI)**: Python-based agent that joins LiveKit rooms to process audio and respond.
- **SIP Client (e.g., Zoiper)**: Softphone for making/receiving calls.

### Call Flow
1. SIP client registers with the SIP bridge.
2. SIP client dials a configured number (e.g., 1001).
3. SIP bridge accepts the call and creates a participant in the specified LiveKit room.
4. Voice bot (already in the room) receives audio from the caller.
5. Bot processes audio, generates response, and sends audio back through LiveKit to the SIP client.

## Architecture

```
SIP Client (Zoiper)
    |
    | SIP Signaling (UDP/TCP 5060)
    v
LiveKit SIP Bridge
    |
    | PSRPC (Redis)
    v
LiveKit Server (WebRTC/WebSocket 7880)
    |
    | Room Audio
    v
Voice Bot (Friday AI)
```

- **Hybrid Knowledge System**: Bot uses static JSON for basic queries + RAG for deep queries.
- **Lead Capture**: Detects intent and captures leads in Hinglish.
- **Audio Pipeline**: STT → Agent Processing → TTS.

## Prerequisites

- WSL (Ubuntu) or Linux environment.
- Go 1.19+ (for building SIP bridge).
- Python 3.10+ (for voice bot).
- Docker (optional, for containerized Redis).

## Installation

### 1. Install Dependencies (WSL Ubuntu)
```bash
sudo apt update
sudo apt install -y curl wget git build-essential redis-server
```

### 2. Install LiveKit Server
```bash
# Method 1: Latest release
wget https://github.com/livekit/livekit/releases/latest/download/livekit-server_Linux_x86_64.tar.gz
tar -xzf livekit-server_Linux_x86_64.tar.gz
sudo mv livekit-server /usr/local/bin/

# Method 2: Specific version (for reproducible deployments)
wget https://github.com/livekit/livekit/releases/download/v1.9.1/livekit-server_1.9.1_linux_amd64.tar.gz
tar -xzf livekit-server_1.9.1_linux_amd64.tar.gz
sudo mv livekit-server /usr/local/bin/
```

### 3. Install LiveKit CLI
```bash
# Method 1: Package manager (latest stable)
curl -sSL https://get.livekit.io/cli | sudo bash

# Method 2: Specific version (reproducible deployments)
CLI_VERSION="1.5.2"
wget -q https://github.com/livekit/livekit-cli/releases/download/v${CLI_VERSION}/livekit-cli_${CLI_VERSION}_linux_amd64.tar.gz
tar -xzf livekit-cli_${CLI_VERSION}_linux_amd64.tar.gz
sudo mv livekit-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/livekit-cli

# Create convenient alias
echo 'alias lk="livekit-cli"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Install LiveKit SIP Bridge
```bash
# Method 1: Build from source (recommended for development)
git clone https://github.com/livekit/livekit-sip.git
cd livekit-sip
go build -o livekit-sip ./cmd/livekit-sip
sudo mv livekit-sip /usr/local/bin/

# Method 2: Download precompiled binary (faster for production)
wget https://github.com/livekit/livekit-sip/releases/download/v1.9.1/livekit-sip_1.9.1_linux_amd64.tar.gz
tar -xzf livekit-sip_1.9.1_linux_amd64.tar.gz
sudo mv livekit-sip /usr/local/bin/
sudo chmod +x /usr/local/bin/livekit-sip
```

### 5. Start Services (using screen)
```bash
# Start LiveKit Server in a detached screen session
screen -dmS livekit-server livekit-server --config /path/to/sip-setup/livekit.yaml

# Start SIP bridge (after LiveKit started)
screen -dmS sip-bridge livekit-sip --config /path/to/sip-setup/config.yaml

# Start agent (from project root)
screen -dmS friday-agent bash -c "cd /path/to/project && source ainvenv/bin/activate && python cagent.py"
```

### 5. Start Redis
```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl status redis-server --no-pager

# Verify Redis is working
redis-cli ping  # Should return PONG
```

## Configuration

### LiveKit Server
Run in dev mode with API keys:
```bash
livekit-server --dev --keys "APIntavBoHTqApw: pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM"
```

### SIP Bridge Config (`sip-setup/config.yaml`)
```yaml
log_level: debug

livekit:
  url: "ws://192.168.109.66:7880"
  api_key: APIntavBoHTqApw
  api_secret: pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM

redis:
  address: localhost:6379
  db: 0

health_port: 8080
prometheus_port: 9090

sip:
  domain: "192.168.109.66"
  port: 5060
  rtp_port: "10000-20000"
  users:
  - user: "1001"
    password: "1001"
    room: "friday-assistant-room"
    participant_identity: "zoiper-caller"
  - user: "bot1"
    password: "botpass"
    room: "friday-assistant-room"
    participant_identity: "voice-bot"
```

- **livekit.url**: WebSocket URL of LiveKit server.
- **sip.domain**: IP address of the SIP server.
- **sip.users**: SIP credentials and room mapping.
- **room**: LiveKit room where calls are bridged (matches `cagent.py` room: "friday-assistant-room").
- **participant_identity**: Identity of the SIP caller/bot in the room.

### Inbound Trunk Config (`inbound-trunk.json`)
```json
{
  "trunk": {
    "name": "local-trunk",
    "auth_username": "sipuser",
    "auth_password": "sipsecret"
  }
}
```
- Defines SIP trunk authentication for inbound calls.
- Used by LiveKit server for trunk management.

### Dispatch Rule Config (`dispatch-rule.json`)
```json
{
  "dispatch_rule": {
    "rule": {
      "dispatchRuleIndividual": {
        "roomPrefix": "friday-"
      }
    }
  },
  "name": "local-dispatch"
}
```
- Configures how inbound SIP calls are dispatched to rooms.
- `roomPrefix`: Prefix for dynamically created rooms (e.g., "friday-assistant-room").

### Voice Bot Configuration
The bot (`cagent.py`) joins the room "friday-assistant-room" (line 44):
```python
await session.start(
    room="friday-assistant-room",
    ...
)
```
Ensure SIP bridge and bot use the same room name for audio exchange.

## Running the Services

### 1. Start LiveKit Server
```bash
livekit-server --dev --keys "APIntavBoHTqApw: pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM"
```

### 2. Start SIP Bridge
```bash
cd sip-setup
./livekit-sip --config config.yaml
```

### 3. Start Voice Bot
```bash
python cagent.py dev
```

### Verify Ports
```bash
ss -tulnp | grep -E "7880|7881|5060"
# OR using netstat
sudo netstat -tunlp | grep -E "7880|7881|5060"
```
Expected output:
- 7880: LiveKit WebSocket
- 7881: LiveKit TCP
- 5060: SIP signaling

### Version Verification
```bash
echo "✅ Installed versions:"
livekit-server --version
livekit-sip --version
livekit-cli --version
redis-cli --version
```

### Alternative: Screen Session Management
```bash
# Install screen for session management
sudo apt install -y screen

# Start services in detached screen sessions
screen -dmS livekit-server bash -c "livekit-server --config /path/to/livekit.yaml"
screen -dmS sip-bridge bash -c "livekit-sip --config /path/to/config.yaml"
screen -dmS friday-agent bash -c "cd /path/to/project && python cagent.py"

# List running sessions
screen -ls

# Attach to a session (Ctrl+A, then D to detach)
screen -r livekit-server
```

## Testing and Verification

### Test with LiveKit CLI
Join the room manually:
```bash
livekit-cli join-room \
  --api-key APIntavBoHTqApw \
  --api-secret pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM \
  --room friday-assistant-room \
  --identity test-user \
  --url ws://192.168.109.66:7880
```

### Test with SIP Client (Zoiper)
1. Configure Zoiper with SIP server: `192.168.109.66:5060`
2. Register as user `1001`, password `1001`.
3. Dial `1001`.
4. Check logs for "INVITE accepted" and room bridging.
5. Voice bot should respond in the room.

### Expected Logs
- SIP Bridge: "processing invite", "SIP invite authentication successful"
- LiveKit: Worker registered, room join events.
- Bot: Conversation logging in `conversations/`.

### Automated SIP Configuration

Instead of manually creating JSON files, you can generate them programmatically:

```bash
# Create inbound trunk configuration
cat <<EOF > inbound_trunk.json
{
  "name": "Zoiper Local Inbound",
  "authUsername": "1001", 
  "authPassword": "1001",
  "mediaEncryption": "SIP_MEDIA_ENCRYPT_DISABLE"
}
EOF

# Create trunk and capture ID
TRUNK_ID=$(lk sip inbound create --project friday inbound_trunk.json | grep "SIPTrunkID:" | awk '{print $2}')
echo "Created trunk with ID: $TRUNK_ID"

# Create dispatch rule with captured trunk ID
cat <<EOF > sip_dispatch.json
{
  "name": "Zoiper Individual Dispatch Rule",
  "trunk_ids": ["$TRUNK_ID"],
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  }
}
EOF

# Create dispatch rule
lk sip dispatch create --project friday sip_dispatch.json

# Verify configuration
lk sip inbound-trunk list
lk sip dispatch list
```

## Integration with Voice Bot

The voice bot (`cagent.py`) uses LiveKit SDK to join rooms. Key integrations:

- **Plugins**: Modified LiveKit plugins in `backup_plugin_modifications/` for STT/TTS.
- **Tools**: Business logic in `tools.py` with `@function_tool()` decorator.
- **Prompts**: Hinglish prompts in `prompts.py`.
- **RAG**: Vector DB in `model/chroma_db/` for knowledge queries.
- **Leads**: Captured in `leads/` with English JSON keys.

Ensure bot joins "friday-assistant-room" to receive SIP calls.

## Troubleshooting

### Common Issues
- **"no response from servers"**: IOInfo service not running; ensure LiveKit server is up and PSRPC registered.
- **SIP auth failed**: Check config.yaml credentials and room mapping.
- **No audio**: Verify RTP ports (10000-20000) are open; check firewall.
- **Redis connection**: Ensure Redis is running on localhost:6379.
- **Bot not responding**: Confirm bot is in the correct room; check LiveKit logs.

### Debugging Commands
- Check Redis: `redis-cli PING`
- View SIP logs: Monitor SIP bridge output.
- Inspect rooms: Use LiveKit CLI to list rooms/participants.
- Rebuild RAG: `python model/build_db.py` after knowledge changes.

### Logs Locations
- SIP Bridge: Console output.
- LiveKit Server: Console or configured log file.
- Bot: `conversations/` for interactions.

## Security Notes
- Protect API secrets; mint tokens only on backend.
- Leads/conversations contain PII; use secure storage.
- Use HTTPS/WebSocket secure in production.

## Code References

### SIP Bridge Code
- **Config Parsing**: `sip/pkg/config/config.go` - Loads YAML config including livekit, sip, redis settings.
- **Inbound Call Handling**: `sip/pkg/sip/inbound.go` - Processes SIP INVITE, authenticates, joins LiveKit room (e.g., `joinRoom` function).
- **Room Management**: `sip/pkg/sip/room.go` - Handles participant joins, audio bridging.
- **Authentication**: `sip/pkg/sip/inbound.go` - SIP digest auth for users like "1001".

### Voice Bot Code
- **Room Joining**: `cagent.py` (line 44) - Joins "friday-assistant-room" via `session.start()`.
- **Tools & Prompts**: `tools.py` - Business logic with `@function_tool()`; `prompts.py` - Hinglish prompts.
- **RAG Integration**: `model/` - Vector DB for knowledge queries.
- **Lead Capture**: `tools.py` - `create_lead()` saves to `leads/` with English JSON keys.

### Configuration Files
- **Trunk Setup**: `inbound-trunk.json` - Defines SIP trunk for LiveKit server.
- **Dispatch Rules**: `dispatch-rule.json` - Rules for routing calls to rooms with "friday-" prefix.
- **Conversation Logs**: `config.py` - Logs saved as `conversations/YYYYMMDD_HHMMSS.json`.

### Key Patterns
- **Hinglish Language**: User-facing strings in `prompts.py` and `tools.py`.
- **JSON Storage**: Leads in English keys; conversations in structured JSON.
- **Plugin Modifications**: `backup_plugin_modifications/` - Patched LiveKit plugins for STT/TTS.

## References
- [LiveKit Documentation](https://docs.livekit.io/)
- [LiveKit SIP Bridge](https://github.com/livekit/livekit-sip)
- Friday AI Copilot Instructions: `.github/copilot-instructions.md`
- SIP Bridge README: `sip-setup/README.md`