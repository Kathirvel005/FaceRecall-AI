import asyncio
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
import cv2
from backend.app.services.camera_service import camera_engine

router = APIRouter(prefix="/camera", tags=["Camera Engine"])

@router.get("/status")
async def get_camera_status():
    return camera_engine.get_status()

@router.post("/start")
async def start_camera():
    started = camera_engine.start()
    return {"success": started, "status": camera_engine.get_status()}

@router.post("/stop")
async def stop_camera():
    camera_engine.stop()
    return {"success": True, "status": camera_engine.get_status()}

@router.get("/snapshot")
async def get_snapshot():
    has_frame, frame, ts, fid = camera_engine.get_latest_frame()
    if not has_frame or frame is None:
        raise HTTPException(status_code=503, detail="Camera frame not available")

    ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode frame")

    return Response(content=buffer.tobytes(), media_type="image/jpeg")

async def mjpeg_generator():
    while True:
        has_frame, frame, ts, fid = camera_engine.get_latest_frame()
        if has_frame and frame is not None:
            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        await asyncio.sleep(0.016)  # ~60 FPS capable, zero latency

@router.get("/stream")
async def get_stream():
    if not camera_engine.get_status()["is_running"]:
        camera_engine.start()
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
