@echo off
REM Set environment variables for LiveKit webhook handler testing
echo Setting up LiveKit environment variables for testing...

set LIVEKIT_URL=ws://127.0.0.1:7880
set LIVEKIT_API_KEY=APIntavBoHTqApw
set LIVEKIT_API_SECRET=pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM

echo Environment variables set:
echo LIVEKIT_URL=%LIVEKIT_URL%
echo LIVEKIT_API_KEY=%LIVEKIT_API_KEY%
echo LIVEKIT_API_SECRET=%LIVEKIT_API_SECRET%

echo.
echo Now you can run:
echo python handler.py
echo.
echo And in another terminal:
echo python test_asterisk_dialed_number.py