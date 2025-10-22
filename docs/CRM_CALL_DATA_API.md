# CRM Call Data API Documentation

## Overview
This document describes the API endpoint for retrieving call data including transcriptions and lead information.

## Payload Details

### Transcription Object Structure
The `transcription` field contains the complete conversation transcript from the voice agent session:

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

**Transcription Fields:**
- `session_id`: Unique identifier for the conversation session
- `start_time`: When the transcription began (ISO 8601 format)
- `end_time`: When the transcription ended (ISO 8601 format)
- `items`: Array of conversation turns
- `total_items`: Total number of conversation items
- `duration_seconds`: Total duration of the transcribed conversation

**Items Array Structure:**
- `role`: Either "user" (caller) or "assistant" (voice agent)
- `content`: The transcribed text content
- `timestamp`: When this conversation turn occurred

### Lead Object Structure
The `lead` field contains information about potential customers captured during the call:

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

**Lead Fields:**
- `name`: Full name of the lead (required)
- `email`: Email address of the lead (required)
- `company`: Company name (required)
- `interest`: What the lead is interested in (required)
- `phone`: Phone number (optional)
- `job_title`: Job title/role (optional)
- `budget`: Budget information (optional)
- `timeline`: Timeline expectations (optional)
- `timestamp`: When the lead was created (ISO 8601 format)
- `source`: Source of the lead (e.g., "Friday AI Assistant")
- `status`: Lead status (e.g., "new", "qualified", "contacted")

## Recent Changes
**October 21, 2025**: Added `transcription` and `lead` fields to the response structure to include conversation data and lead capture information.

### Migration Guide
The API response has been updated to include two new fields:

- `transcription`: Contains the full conversation transcript
- `lead`: Contains lead information captured during the call

**Old Response Structure:**
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

**New Response Structure:**
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

## Endpoint
```
GET https://devcrm.xeny.ai/apis/api/public/call-data
```

## Request
The API accepts query parameters to filter call data:

- `campaignId` (optional): Filter by campaign ID
- `voiceAgentId` (optional): Filter by voice agent ID
- `callId` (optional): Filter by specific call ID
- `startDate` (optional): Filter calls from this date (ISO 8601 format)
- `endDate` (optional): Filter calls until this date (ISO 8601 format)
- `limit` (optional): Maximum number of records to return (default: 50, max: 1000)
- `offset` (optional): Number of records to skip for pagination (default: 0)

### Example Request
```
GET https://devcrm.xeny.ai/apis/api/public/call-data?campaignId=68c91223fde0aa95caa3dbe4&limit=10
```

## Response

### Success Response (200 OK)
```json
{
  "success": true,
  "data": [
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
      },
      "lead": {
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
    }
  ],
  "pagination": {
    "total": 1250,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

### Field Descriptions

#### Root Level Fields
- `campaignId`: Unique identifier for the campaign
- `voiceAgentId`: Unique identifier for the voice agent
- `client`: Unique identifier for the client
- `callDetails`: Object containing call metadata
- `caller`: Object containing caller information
- `transcription`: Object containing conversation transcription data
- `lead`: Object containing lead information (if captured during call)

#### callDetails Object
- `callId`: Unique call identifier
- `direction`: Call direction ("inbound" or "outbound")
- `startTime`: Call start time in ISO 8601 format
- `endTime`: Call end time in ISO 8601 format
- `duration`: Call duration in seconds
- `status`: Call status ("completed", "failed", "missed", etc.)
- `recordingUrl`: URL to the call recording file (optional)
- `recordingDuration`: Recording duration in seconds (optional)
- `recordingSize`: Recording file size in bytes (optional)
- `callerNumber`: Caller's phone number

#### caller Object
- `phoneNumber`: Caller's phone number

#### transcription Object
- `session_id`: Unique session identifier
- `start_time`: Transcription start time
- `end_time`: Transcription end time
- `items`: Array of conversation items
- `total_items`: Total number of conversation items
- `duration_seconds`: Total transcription duration

#### transcription.items Array
Each item represents a turn in the conversation:
- `role`: "user" or "assistant"
- `content`: The spoken text
- `timestamp`: When this turn occurred

#### lead Object
Contains lead information captured during the call:
- `name`: Lead's full name
- `email`: Lead's email address
- `company`: Company name
- `interest`: What the lead is interested in
- `phone`: Lead's phone number
- `job_title`: Lead's job title (optional)
- `budget`: Budget information (optional)
- `timeline`: Timeline information (optional)
- `timestamp`: When the lead was created
- `source`: Source of the lead
- `status`: Lead status

### Error Responses

#### 400 Bad Request
```json
{
  "success": false,
  "error": "Invalid request parameters",
  "message": "startDate must be before endDate"
}
```

#### 404 Not Found
```json
{
  "success": false,
  "error": "No data found",
  "message": "No call data found for the specified criteria"
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Authentication
This endpoint may require authentication. Include the appropriate headers as per your CRM API authentication mechanism.

## Rate Limiting
- 100 requests per minute per API key
- 1000 requests per hour per API key

## Notes
- All timestamps are in UTC and ISO 8601 format
- The `transcription` and `lead` fields may be empty objects `{}` if no data is available
- Pagination is required for large result sets
- Recording URLs are temporary and may expire</content>
<parameter name="filePath">e:\livekitVoiceAgent\CRM_CALL_DATA_API.md