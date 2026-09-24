# REST & WebSocket API Reference

The backend exposes a high-performance asynchronous API conforming to OpenAPI 3.0 standards.

Interactive Swagger documentation is accessible at `http://localhost:8000/docs`.

---

## 1. System & Health

### `GET /health`
Returns system operational status and uptime.

**Response (200 OK):**
```json
{
  "status": "HEALTHY",
  "timestamp": 1727187600.0,
  "uptime_seconds": 124.5,
  "version": "1.0.0"
}
```

### `GET /system/info`
Returns CPU, RAM, GPU, active models, and hardware metrics.

---

## 2. Camera Management

### `GET /camera/status`
Returns camera connection state, resolution, current FPS, and dropped frames.

### `POST /camera/start`
Starts camera capture thread.

### `POST /camera/stop`
Stops camera capture thread cleanly.

### `GET /camera/snapshot`
Returns the latest raw camera frame encoded as JPEG.

### `GET /camera/stream`
MJPEG multipart stream (`multipart/x-mixed-replace; boundary=frame`) for zero-latency camera preview in any browser.

---

## 3. Person Management & Enrollment

### `GET /persons`
Lists all registered students/persons with their enrolled sample counts.

**Query Parameters:**
- `skip`: (integer, default 0)
- `limit`: (integer, default 100)
- `search`: (string, optional filter by name, student ID, or department)

### `POST /persons`
Registers a new person profile.

**Request Body:**
```json
{
  "student_id": "STU001",
  "name": "Kathirvel",
  "department": "Computer Science",
  "class_name": "CSE-A",
  "email": "kathirvel@example.com",
  "active": true
}
```

### `GET /persons/{id}`
Returns person details and their individual face sample metadata.

### `PUT /persons/{id}`
Updates person metadata.

### `DELETE /persons/{id}`
Deletes person record from database, purges all stored face sample images from disk, and removes their biometric embeddings from the FAISS vector index.

### `POST /persons/{id}/enroll`
Batch enrollment endpoint. Accepts 10–20 face sample crops (base64 encoded), evaluates quality, detects landmarks, computes ArcFace embeddings, and indexes them in FAISS.

**Request Body:**
```json
{
  "samples": [
    {"image_base64": "data:image/jpeg;base64,...", "quality_score": 1.0}
  ]
}
```

---

## 4. Real-Time Recognition

### `POST /recognition/start`
Starts the real-time detection, tracking, and recognition pipeline.

### `POST /recognition/stop`
Pauses the real-time recognition pipeline.

### `GET /recognition/status`
Returns current pipeline activity, processed frames count, active tracks, and last inference latency.

### `GET /statistics`
Aggregates registered persons, total events, known events, unknown events, and live pipeline metrics.

---

## 5. WebSocket Real-Time Stream

### `WS /ws/recognition`
Streams structured JSON frame updates containing multi-face detection bounding boxes, persistent track IDs, identities, similarity scores, quality metrics, and timestamp.

**Sample Message:**
```json
{
  "frame_id": 142,
  "timestamp": "2026-09-24T19:40:00Z",
  "camera_id": "cam-0",
  "fps": 28.5,
  "face_count": 2,
  "known_count": 1,
  "unknown_count": 1,
  "inference_latency_ms": 38.4,
  "faces": [
    {
      "track_id": 1,
      "person_id": "STU001",
      "name": "Kathirvel",
      "status": "KNOWN",
      "similarity": 0.924,
      "quality": 0.885,
      "bbox": [180, 120, 310, 290],
      "is_live": true,
      "timestamp": "2026-09-24T19:40:00Z"
    },
    {
      "track_id": 2,
      "person_id": null,
      "name": "UNKNOWN",
      "status": "UNKNOWN",
      "similarity": 0.281,
      "quality": 0.742,
      "bbox": [450, 160, 560, 310],
      "is_live": true,
      "timestamp": "2026-09-24T19:40:00Z"
    }
  ]
}
```
