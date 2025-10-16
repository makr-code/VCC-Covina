# Review Queue REST API Documentation

## Overview

The Review Queue API provides endpoints for managing data quality gap review tasks created by the Handelsregister integration. When company extraction detects missing or incomplete data (e.g., missing HRB number, missing court), review tasks are automatically created in PostgreSQL for manual resolution.

**Base URL:** `http://localhost:8000/api/review-tasks`

---

## Authentication

Currently no authentication required (MVP). In production, add JWT/OAuth2.

---

## Endpoints

### 1. GET /api/review-tasks

Query review tasks with filters and pagination.

**Parameters:**
- `status` (string, optional): Filter by status (pending | in_progress | resolved | dismissed)
- `severity` (string, optional): Filter by severity (low | medium | high | critical)
- `gap_type` (string, optional): Filter by gap type (missing_register_number | missing_register_court | verification_failed)
- `document_id` (string, optional): Filter by document ID
- `assigned_to` (string, optional): Filter by assigned user
- `limit` (int, optional, default=100, max=1000): Maximum results
- `offset` (int, optional, default=0): Offset for pagination

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/review-tasks?status=pending&severity=high&limit=50"
```

**Example Response:**
```json
{
  "tasks": [
    {
      "review_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_id": "doc_12345",
      "file_path": "/uploads/example.pdf",
      "gap_type": "missing_register_number",
      "firma": "Test GmbH",
      "severity": "medium",
      "message": "Company 'Test GmbH' has no HRB/HRA number",
      "status": "pending",
      "created_at": "2025-10-10T12:00:00",
      "updated_at": null,
      "assigned_to": null,
      "resolved_at": null,
      "resolution_notes": null,
      "metadata": null
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

---

### 2. GET /api/review-tasks/statistics

Get aggregated statistics about review tasks.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/review-tasks/statistics"
```

**Example Response:**
```json
{
  "total_tasks": 42,
  "by_status": {
    "pending": 15,
    "in_progress": 10,
    "resolved": 12,
    "dismissed": 5
  },
  "by_severity": {
    "low": 8,
    "medium": 20,
    "high": 12,
    "critical": 2
  },
  "by_gap_type": {
    "missing_register_number": 25,
    "missing_register_court": 12,
    "verification_failed": 5
  },
  "avg_resolution_time_hours": 4.5
}
```

---

### 3. GET /api/review-tasks/{review_id}

Get a single review task by ID.

**Parameters:**
- `review_id` (string, required): UUID of the review task

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/review-tasks/550e8400-e29b-41d4-a716-446655440000"
```

**Example Response:**
```json
{
  "review_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_12345",
  "file_path": "/uploads/example.pdf",
  "gap_type": "missing_register_number",
  "firma": "Test GmbH",
  "severity": "medium",
  "message": "Company 'Test GmbH' has no HRB/HRA number",
  "status": "pending",
  "created_at": "2025-10-10T12:00:00",
  "updated_at": null,
  "assigned_to": null,
  "resolved_at": null,
  "resolution_notes": null,
  "metadata": null
}
```

**Error Response (404):**
```json
{
  "detail": "Review Task 550e8400-... nicht gefunden"
}
```

---

### 4. PUT /api/review-tasks/{review_id}/status

Update review task status.

**Parameters:**
- `review_id` (string, required): UUID of the review task

**Request Body:**
```json
{
  "status": "resolved",
  "resolution_notes": "Fixed manually - added HRB 12345 from company website"
}
```

**Fields:**
- `status` (string, required): New status (pending | in_progress | resolved | dismissed)
- `resolution_notes` (string, optional): Resolution notes (REQUIRED for status='resolved')

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/api/review-tasks/550e8400-.../status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_notes": "Fixed manually - added HRB 12345"
  }'
```

**Example Response:**
```json
{
  "success": true,
  "review_id": "550e8400-e29b-41d4-a716-446655440000",
  "old_status": "in_progress",
  "new_status": "resolved",
  "resolved_at": "2025-10-10T14:30:00",
  "message": "Status erfolgreich aktualisiert: in_progress → resolved"
}
```

**Error Response (400 - Missing resolution_notes):**
```json
{
  "detail": "resolution_notes erforderlich für Status 'resolved'"
}
```

**Error Response (400 - Invalid status):**
```json
{
  "detail": "Ungültiger Status: invalid_status. Erlaubt: ['pending', 'in_progress', 'resolved', 'dismissed']"
}
```

---

### 5. PUT /api/review-tasks/{review_id}/assign

Assign review task to a user.

**Parameters:**
- `review_id` (string, required): UUID of the review task

**Request Body:**
```json
{
  "assigned_to": "user@example.com"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/api/review-tasks/550e8400-.../assign" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to": "reviewer@example.com"
  }'
```

**Example Response:**
```json
{
  "success": true,
  "review_id": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_to": "reviewer@example.com",
  "message": "Task erfolgreich zugewiesen an reviewer@example.com"
}
```

---

### 6. DELETE /api/review-tasks/{review_id}

Delete a review task.

**Parameters:**
- `review_id` (string, required): UUID of the review task

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/review-tasks/550e8400-e29b-41d4-a716-446655440000"
```

**Example Response:**
```json
{
  "success": true,
  "review_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task erfolgreich gelöscht"
}
```

**Error Response (404):**
```json
{
  "detail": "Review Task 550e8400-... nicht gefunden"
}
```

---

## Data Models

### ReviewTaskResponse

```typescript
{
  review_id: string           // UUID
  document_id: string          // Document ID from PostgreSQL
  file_path?: string           // Path to document file
  gap_type: string             // missing_register_number | missing_register_court | verification_failed
  firma?: string               // Company name
  severity: string             // low | medium | high | critical
  message: string              // Descriptive error message
  status: string               // pending | in_progress | resolved | dismissed
  created_at: string           // ISO 8601 timestamp
  updated_at?: string          // ISO 8601 timestamp
  assigned_to?: string         // User email/ID
  resolved_at?: string         // ISO 8601 timestamp
  resolution_notes?: string    // Resolution notes
  metadata?: object            // Additional metadata (JSONB)
}
```

### Gap Types

- **missing_register_number**: Company mentioned but no HRB/HRA number found (Severity: MEDIUM)
- **missing_register_court**: Company mentioned but no register court found (Severity: LOW)
- **verification_failed**: Handelsregister API verification failed (Severity: HIGH)

### Severity Levels

- **low**: Minor issue, can be resolved later
- **medium**: Important issue, should be resolved soon
- **high**: Critical issue, requires immediate attention
- **critical**: Blocking issue, must be resolved before proceeding

### Status Values

- **pending**: Newly created, awaiting assignment
- **in_progress**: Assigned and being worked on
- **resolved**: Completed successfully
- **dismissed**: Rejected/cancelled

---

## Workflow Example

```bash
# 1. Query pending high-severity tasks
curl -X GET "http://localhost:8000/api/review-tasks?status=pending&severity=high"

# 2. Get specific task
curl -X GET "http://localhost:8000/api/review-tasks/550e8400-..."

# 3. Assign to user
curl -X PUT "http://localhost:8000/api/review-tasks/550e8400-.../assign" \
  -H "Content-Type: application/json" \
  -d '{"assigned_to": "reviewer@example.com"}'

# 4. Update status to in_progress
curl -X PUT "http://localhost:8000/api/review-tasks/550e8400-.../status" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# 5. Resolve task
curl -X PUT "http://localhost:8000/api/review-tasks/550e8400-.../status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_notes": "Found HRB 12345 on company website - updated metadata"
  }'

# 6. Check statistics
curl -X GET "http://localhost:8000/api/review-tasks/statistics"
```

---

## Error Codes

- **400 Bad Request**: Invalid request (e.g., missing resolution_notes, invalid status)
- **404 Not Found**: Review task not found
- **500 Internal Server Error**: Database error or service unavailable
- **503 Service Unavailable**: Review Queue service not initialized

---

## Integration with Handelsregister Pipeline

Review tasks are automatically created during document upload when gaps are detected:

```
POST /upload/files
  ↓
process_document_with_uds3()
  ↓
Company Extraction [Lines 2293-2440]
  ↓
Gap Detection
  ↓
CREATE REVIEW TASKS [Lines 2373-2398]
  ├─ missing_register_number → severity: MEDIUM
  ├─ missing_register_court → severity: LOW
  └─ verification_failed → severity: HIGH
  ↓
Store in PostgreSQL review_tasks table
```

---

## Database Schema

```sql
CREATE TABLE review_tasks (
    review_id UUID PRIMARY KEY,
    document_id TEXT REFERENCES documents(document_id) ON DELETE CASCADE,
    file_path TEXT,
    gap_type TEXT,
    firma TEXT,
    severity TEXT,
    message TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    assigned_to TEXT,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    metadata JSONB
);

CREATE INDEX idx_review_tasks_status ON review_tasks(status);
CREATE INDEX idx_review_tasks_severity ON review_tasks(severity);
CREATE INDEX idx_review_tasks_created_at ON review_tasks(created_at DESC);
CREATE INDEX idx_review_tasks_document_id ON review_tasks(document_id);
CREATE INDEX idx_review_tasks_gap_type ON review_tasks(gap_type);
```

---

## Rate Limiting

Currently no rate limiting. In production, consider adding:
- Per-user rate limits (e.g., 100 requests/minute)
- IP-based rate limits
- Redis-based token bucket

---

## Future Enhancements

1. **Bulk Operations**
   ```
   PUT /api/review-tasks/bulk/assign
   PUT /api/review-tasks/bulk/status
   DELETE /api/review-tasks/bulk
   ```

2. **Task Comments/History**
   ```
   POST /api/review-tasks/{review_id}/comments
   GET /api/review-tasks/{review_id}/history
   ```

3. **Email Notifications**
   - Automatic emails for new high/critical severity tasks
   - Assignment notifications
   - Resolution confirmations

4. **Webhooks**
   ```
   POST /api/review-tasks/webhooks
   ```
   - Trigger external systems on task events

5. **Advanced Filtering**
   ```
   GET /api/review-tasks?created_after=2025-10-01&created_before=2025-10-10
   GET /api/review-tasks?firma=Test%20GmbH
   ```

---

## Testing

Run the test suite:
```bash
# Start backend
python backend.py

# Run API tests
python scripts/test_review_queue_api.py
```

Expected output:
```
✅ GET /api/review-tasks
✅ GET /api/review-tasks?status=pending
✅ GET /api/review-tasks?severity=medium
✅ GET /api/review-tasks/{review_id}
✅ PUT /api/review-tasks/{review_id}/assign
✅ PUT /api/review-tasks/{review_id}/status
✅ GET /api/review-tasks/statistics
⏭️  DELETE /api/review-tasks/{review_id} (SKIPPED)

Success rate: 100.0%
```

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0  
**Status:** Production Ready ✅
