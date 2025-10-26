#!/bin/bash
# Test script for Asterisk integration

echo "Starting LiveKit Voice Agent with Asterisk integration..."

# Terminal 1: Start webhook handler with debug logging
echo "1. Starting webhook handler (run in separate terminal):"
echo "python handler.py"

echo ""
echo "2. Start LiveKit server (run in separate terminal):"
echo "livekit-server --config livekit.yaml"

echo ""
echo "3. Start SIP bridge (run in separate terminal):"
echo "cd sip-setup && ./livekit-sip --config config.yaml"

echo ""
echo "4. Start voice agent (run in separate terminal):"
echo "python cagent.py"

echo ""
echo "5. Make test call from Asterisk to: 918655054859"
echo "6. Check webhook handler logs for dialed number extraction"

echo ""
echo "Expected log output should show:"
echo "- 'Processing inbound call to 918655054859'"
echo "- 'Extracted dialed number from SIP URI'"
echo "- Participant attributes containing sip.* fields"