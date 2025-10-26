# PowerShell script to set up environment variables for testing
Write-Host "Setting up LiveKit environment variables for testing..." -ForegroundColor Green

$env:LIVEKIT_URL = "ws://127.0.0.1:7880"
$env:LIVEKIT_API_KEY = "APIntavBoHTqApw"
$env:LIVEKIT_API_SECRET = "pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM"

Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "LIVEKIT_URL: $env:LIVEKIT_URL"
Write-Host "LIVEKIT_API_KEY: $env:LIVEKIT_API_KEY"
Write-Host "LIVEKIT_API_SECRET: $env:LIVEKIT_API_SECRET"

Write-Host ""
Write-Host "Now you can run:" -ForegroundColor Cyan
Write-Host "python handler.py" -ForegroundColor White
Write-Host ""
Write-Host "And in another terminal:" -ForegroundColor Cyan
Write-Host "python test_asterisk_dialed_number.py" -ForegroundColor White