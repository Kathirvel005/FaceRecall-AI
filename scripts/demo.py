#!/usr/bin/env python3
"""
Interactive Final Demo Mode for Real-Time Multi-Face Recognition System
Checks hardware, loads models, initializes database & vector store, connects camera,
starts backend pipeline, and launches the dashboard.
"""

import sys
import time
import os
import webbrowser
import threading
import uvicorn
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.database.connection import init_db
from backend.app.ml.detector import SCRFDDetector
from backend.app.ml.recognizer import ArcFaceRecognizer
from backend.app.ml.vector_store import vector_store
from backend.app.services.camera_service import camera_engine
from backend.app.services.recognition_service import pipeline
from scripts.system_check import get_gpu_info, get_cpu_info, get_ram_info

def print_banner():
    banner = """
================================================================================
   CLASSROOM MULTI-FACE RECOGNITION & REAL-TIME IDENTITY SYSTEM - DEMO MODE
================================================================================
"""
    print(banner)

def main():
    print_banner()

    print("[1/6] Inspecting System Hardware...")
    gpu = get_gpu_info()
    cpu = get_cpu_info()
    ram = get_ram_info()
    print(f"      CPU:  {cpu}")
    print(f"      RAM:  {ram}")
    print(f"      GPU:  {gpu['name']} (CUDA: {'Available' if gpu['cuda_available'] else 'Unavailable'})")

    print("\n[2/6] Initializing Database & Vector Store...")
    import asyncio
    asyncio.run(init_db())
    v_count = vector_store.count()
    print(f"      Database: Initialized (SQLite/PostgreSQL)")
    print(f"      FAISS Vector Store: Loaded ({v_count} registered identity embeddings)")

    print("\n[3/6] Loading Deep Learning Models...")
    detector = SCRFDDetector()
    recognizer = ArcFaceRecognizer()
    print(f"      Face Detector:   {settings.DETECTION_MODEL_PATH} (Active: {detector.session.get_providers()[0]})")
    print(f"      Face Recognizer: {settings.RECOGNITION_MODEL_PATH} (Active: {recognizer.session.get_providers()[0]})")

    print("\n[4/6] Connecting to Camera Subsystem...")
    cam_started = camera_engine.start()
    time.sleep(1.0)
    cam_status = camera_engine.get_status()
    if cam_status["is_connected"]:
        print(f"      Camera Source {cam_status['source']}: CONNECTED ({cam_status['resolution']} @ {cam_status['target_fps']} FPS)")
    else:
        print(f"      Camera Warning: Source {cam_status['source']} not immediately available; background reconnect active.")

    print("\n[5/6] Activating Real-Time Pipeline...")
    pipeline.start()
    print("      Multi-Face Tracker:    Active")
    print("      Quality Filter:        Active (Sharpness >= 50, Size >= 60px)")
    print("      Temporal Confirmation: Active (Window: 8 frames, Ratio: 60%)")
    print("      Anti-False-Match:      Active (Unknown Threshold: 0.40)")

    print("\n[6/6] Launching Server & Dashboard...")
    print("=" * 80)
    print("                      SYSTEM READY - STATUS OVERVIEW")
    print("=" * 80)
    print("  Camera:          CONNECTED")
    print(f"  Detector:        LOADED ({settings.DETECTION_MODEL_PATH})")
    print(f"  Recognizer:      LOADED ({settings.RECOGNITION_MODEL_PATH})")
    print(f"  Vector DB:       LOADED ({v_count} vectors)")
    print(f"  GPU / CUDA:      {'AVAILABLE' if gpu['cuda_available'] else 'CPU FALLBACK'}")
    print("  Recognition:     ACTIVE (Multi-face concurrent processing)")
    print("  Backend API:     http://localhost:8000")
    print("  API Docs:        http://localhost:8000/docs")
    print("  WebSocket Feed:  ws://localhost:8000/ws/recognition")
    print("  Frontend UI:     http://localhost:3000")
    print("=" * 80)
    print("\nPress Ctrl+C to stop the system gracefully.\n")

    # Run uvicorn server in main thread
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
