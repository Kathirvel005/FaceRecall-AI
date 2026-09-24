import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.database.connection import init_db
from backend.app.ml.vector_store import vector_store
from backend.app.services.recognition_service import pipeline
from backend.app.api.routes import health, camera, persons, recognition, events

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Classroom Multi-Face Recognition System...")
    # Initialize database
    await init_db()
    logger.info(f"FAISS Vector Store initialized with {vector_store.count()} indexed embeddings.")
    # Mount static face sample files
    settings.FACES_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    logger.info("Shutting down recognition pipeline and camera...")
    pipeline.stop()
    pipeline.camera.stop()
    logger.info("System shutdown complete.")

app = FastAPI(
    title="Advanced Classroom Multi-Face Recognition & Identity System",
    description="Production-grade real-time multi-face detection, tracking, ArcFace recognition, and identity verification API.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for stored face crops
app.mount("/data/faces", StaticFiles(directory=str(settings.FACES_DIR)), name="faces")

# Register Routers
app.include_router(health.router)
app.include_router(camera.router)
app.include_router(persons.router)
app.include_router(recognition.router)
app.include_router(events.router)

@app.get("/")
async def root():
    return {
        "system": "Classroom Multi-Face Identity System",
        "docs_url": "/docs",
        "health_check": "/health",
        "websocket_url": "/ws/recognition"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
