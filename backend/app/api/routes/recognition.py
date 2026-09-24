import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.database.connection import get_db
from backend.app.database.repositories import RecognitionEventRepository
from backend.app.services.recognition_service import pipeline
from backend.app.schemas.recognition import RecognitionFrameSummary, RecognitionEventResponse

router = APIRouter(prefix="", tags=["Recognition & Real-Time Stream"])

@router.post("/recognition/start")
async def start_recognition():
    pipeline.start()
    return {"success": True, "message": "Real-time recognition pipeline started."}

@router.post("/recognition/stop")
async def stop_recognition():
    pipeline.stop()
    return {"success": True, "message": "Real-time recognition pipeline stopped."}

@router.get("/recognition/status")
async def get_recognition_status():
    summary = pipeline.latest_summary
    return {
        "is_active": pipeline._is_active,
        "processed_frames": pipeline.frame_count,
        "inference_latency_ms": pipeline.last_latency_ms,
        "active_tracks": len(pipeline.tracker.tracks),
        "latest_summary": summary
    }

@router.get("/recognition/events", response_model=List[RecognitionEventResponse])
async def get_recognition_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    events = await RecognitionEventRepository.get_recent(db, limit=limit)
    responses = []
    for e in events:
        responses.append(RecognitionEventResponse(
            id=e.id,
            person_id=e.person_id,
            student_id=e.person.student_id if e.person else None,
            name=e.person.name if e.person else "UNKNOWN",
            track_id=e.track_id,
            status=e.status,
            similarity=e.similarity,
            quality=e.quality,
            camera_id=e.camera_id,
            bbox=e.bbox,
            timestamp=e.timestamp
        ))
    return responses

@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    stats = await RecognitionEventRepository.get_statistics(db)
    stats.update({
        "pipeline_active": pipeline._is_active,
        "camera_fps": pipeline.camera.get_status().get("current_fps", 0.0),
        "inference_latency_ms": pipeline.last_latency_ms,
        "vector_db_size": pipeline.store.count()
    })
    return stats

@router.websocket("/ws/recognition")
async def websocket_recognition_endpoint(websocket: WebSocket):
    """
    High-Performance Real-Time WebSocket Endpoint.
    Streams JSON recognition frame summaries (bounding boxes, names, similarity, quality, track IDs).
    """
    await websocket.accept()
    logger.info("New WebSocket client connected to /ws/recognition")

    # Ensure pipeline is started when client connects
    if not pipeline._is_active:
        pipeline.start()

    queue = pipeline.subscribe()
    try:
        while True:
            # Non-blocking get with timeout
            try:
                summary: RecognitionFrameSummary = await asyncio.wait_for(queue.get(), timeout=2.0)
                await websocket.send_json(summary.model_dump())
            except asyncio.TimeoutError:
                # Keep-alive ping
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/recognition")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        pipeline.unsubscribe(queue)
