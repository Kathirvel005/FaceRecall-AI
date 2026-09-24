import time
import platform
import psutil
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.ml.vector_store import vector_store
from backend.app.services.camera_service import camera_engine

router = APIRouter(prefix="", tags=["System & Health"])

START_TIME = time.time()

@router.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "timestamp": time.time(),
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": "1.0.0"
    }

@router.get("/system/info")
async def system_info():
    mem = psutil.virtual_memory()
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "ram_available_gb": round(mem.available / (1024 ** 3), 2),
        "ram_percent": mem.percent,
        "active_models": {
            "detector": settings.DETECTION_MODEL_PATH,
            "recognizer": settings.RECOGNITION_MODEL_PATH
        },
        "vector_store_count": vector_store.count(),
        "camera_status": camera_engine.get_status()
    }
