# API Update: Add Transcription and Lead Fields

## Summary
Update the `GET /apis/api/public/call-data` endpoint to include `transcription` and `lead` fields in the response.

## Payload Details

### Transcription Object
The `transcription` field should contain the complete conversation transcript:

```json
{
  "session_id": "session_12345",
  "start_time": "2025-09-29T10:15:00.000Z",
  "end_time": "2025-09-29T10:20:30.000Z",
  "items": [
    {
      "role": "user",
      "content": "Hello, I need information about your services",
      "timestamp": "2025-09-29T10:15:05.000Z"
    },
    {
      "role": "assistant",
      "content": "Hello! I'd be happy to help you with information about our services.",
      "timestamp": "2025-09-29T10:15:10.000Z"
    }
  ],
  "total_items": 2,
  "duration_seconds": 330
}
```

### Lead Object
The `lead` field should contain lead information captured during the call:

```json
{
  "name": "John Doe",
  "email": "john.doe@company.com",
  "company": "Tech Corp",
  "interest": "AI Voice Bot",
  "phone": "+919876543210",
  "job_title": "CTO",
  "budget": "50k-100k",
  "timeline": "Q1 2025",
  "timestamp": "2025-09-29T10:18:00.000Z",
  "source": "Friday AI Assistant",
  "status": "new"
}
```

## Change Required

### Current Response Structure:
```json
{
    "campaignId": "68c91223fde0aa95caa3dbe4",
    "voiceAgentId": "68c9105cfde0aa95caa3db64",
    "client": "68c90d626052ee95ac77059d",
    "callDetails": {
        "callId": "CALL-20250929-001",
        "direction": "inbound",
        "startTime": "2025-09-29T10:15:00.000Z",
        "endTime": "2025-09-29T10:20:30.000Z",
        "duration": 330,
        "status": "completed",
        "recordingUrl": "http://devcrm.xeny.ai/apis/uploads/recordings/1759173049893.wav",
        "recordingDuration": 330,
        "recordingSize": 2456789,
        "callerNumber": "+919876543210"
    },
    "caller": {
        "phoneNumber": "+919876543210"
    }
}
```

### Updated Response Structure:
```json
{
    "campaignId": "68c91223fde0aa95caa3dbe4",
    "voiceAgentId": "68c9105cfde0aa95caa3db64",
    "client": "68c90d626052ee95ac77059d",
    "callDetails": {
        "callId": "CALL-20250929-001",
        "direction": "inbound",
        "startTime": "2025-09-29T10:15:00.000Z",
        "endTime": "2025-09-29T10:20:30.000Z",
        "duration": 330,
        "status": "completed",
        "recordingUrl": "http://devcrm.xeny.ai/apis/uploads/recordings/1759173049893.wav",
        "recordingDuration": 330,
        "recordingSize": 2456789,
        "callerNumber": "+919876543210"
    },
    "caller": {
        "phoneNumber": "+919876543210"
    },
    "transcription": {

    },
    "lead": {

    }
}
```

## Implementation Notes

1. **transcription** field: Should contain the conversation transcript data from the voice agent session
2. **lead** field: Should contain lead information captured during the call
3. Both fields should be objects, defaulting to empty objects `{}` when no data is available
4. Ensure backward compatibility - existing API consumers should not break
5. Update any database queries to include transcription and lead data retrieval

## Files to Update
- Backend API endpoint handler for `/apis/api/public/call-data`
- Database query logic to fetch transcription and lead data
- API response serialization logic

## Testing
- Verify existing API consumers still work
- Test with calls that have transcription and lead data
- Test with calls that don't have transcription/lead data (should return empty objects)
