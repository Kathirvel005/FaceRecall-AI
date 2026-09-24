# Advanced Multi-Face Recognition & Real-Time Classroom Identity System

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-1.30-purple.svg)](https://onnxruntime.ai/)
[![FAISS](https://img.shields.io/badge/FAISS-CPU%2FGPU-orange.svg)](https://github.com/facebookresearch/faiss)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A complete, production-grade **real-time multi-face detection, tracking, and identity verification system** engineered for classroom environments. Simultaneously detects multiple faces across video streams, validates image quality, extracts 512-D ArcFace embeddings, searches identities in sub-millisecond vector indices with FAISS, applies temporal smoothing to eliminate identity flickering, distinguishes registered students from unregistered visitors (`UNKNOWN`), and displays live results on a real-time dashboard.

---

## 🌟 Key Engineering Features

- **Multi-Face Concurrent Detection:** SCRFD ResNet-10G detector locates multiple faces simultaneously at various distances and orientations with 5 facial keypoints.
- **Deep Biometric Feature Representation:** ArcFace 512-dimensional L2-normalized embeddings for high inter-class variance and compact intra-class variance.
- **Sub-Millisecond Vector Search:** Integrated FAISS index (`IndexFlatIP`) performing cosine similarity lookups in < 0.1ms for 100+ identities.
- **Persistent Multi-Face Tracking:** IoU-based multi-object tracker maintains track IDs across frames and handles occlusion, avoiding expensive recognition on every frame.
- **Multi-Factor Face Quality Assessment:** Evaluates face size ($\ge 60\text{px}$), motion blur ($\sigma^2_{\text{Laplacian}} \ge 50$), brightness ($40 \le I \le 220$), and 3D pose angles (Yaw, Pitch, Roll) from facial geometry.
- **Anti-False-Match & Temporal Verification:** Sliding-window observation buffer with 60% agreement confirmation to eliminate identity flickering.
- **Explicit Unknown Detection:** Unregistered individuals are distinctly marked as `UNKNOWN` rather than forced to the closest match.
- **Modular Hardware Acceleration:** Auto-detects NVIDIA GPUs, selecting `CUDAExecutionProvider` when available with seamless CPU fallback.
- **Zero-Latency Camera Subsystem:** Decoupled multi-threaded capture with frame-dropping mechanism and automatic reconnection.
- **Modern Next.js Dashboard:** Live camera view with color-coded bounding boxes (`KNOWN`, `UNKNOWN`, `LOW_QUALITY`, `VERIFYING`), interactive enrollment UI, and event audit logs.

---

## 🏗️ System Architecture

```
Camera Stream (Webcam / USB / RTSP)
   │
   ▼
Frame Dropper (Non-blocking latest frame buffer)
   │
   ▼
Face Detector (SCRFD ONNX with 5 Keypoints)
   │
   ▼
Multi-Face Tracker (Persistent Track IDs)
   │
   ▼
Face Quality Analyzer (Size, Sharpness, Brightness, Pose)
   │
   ▼
ArcFace Alignment & 512-D Feature Embedding
   │
   ▼
FAISS Nearest Neighbor Vector Search
   │
   ▼
Identity Matching & Anti-False-Match Guard
   │
   ▼
Temporal Smoothing Buffer (Voting across 8 frames)
   │
   ▼
FastAPI WebSocket Broadcast (/ws/recognition)
   │
   ▼
Next.js React Dashboard (Live Canvas Overlays)
```

---

## 🚀 Quick Start

### 1. Hardware Inspection
```powershell
python scripts/system_check.py
```

### 2. Run Automated Test Suite
```powershell
$env:PYTHONPATH="."
pytest tests/ -v
```

### 3. Launch Demo Mode (Complete Integrated System)
```powershell
python scripts/demo.py
```

Open your browser at:
- **Web Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Camera Stream:** [http://localhost:8000/camera/stream](http://localhost:8000/camera/stream)

---

## 📊 Performance Benchmarks & Validation

Run the benchmark suite:
```powershell
python scripts/benchmark.py
```

Run the threshold calibration utility:
```powershell
python scripts/calibrate_threshold.py
```

- **FAISS Nearest Neighbor Latency:** ~0.096 ms
- **ArcFace Feature Extraction Latency:** ~63.8 ms (CPU) / ~12 ms (GPU)
- **SCRFD Detection Latency (720p):** ~165 ms (ResNet-10G) / ~38 ms (500M)
- **Calibrated Operating Thresholds:**
  - `SIMILARITY_THRESHOLD`: `0.50` (Confident student identification)
  - `UNKNOWN_THRESHOLD`: `0.40` (Explicit rejection of unregistered visitors)

---

## 📂 Project Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/          # REST & WebSocket Endpoints
│   │   ├── core/                # Logging & JWT Security
│   │   ├── database/            # SQLAlchemy Engine & Repositories
│   │   ├── ml/                  # SCRFD, ArcFace, FAISS, Tracker
│   │   ├── models/              # Database Schema Models
│   │   ├── schemas/             # Pydantic Request/Response Types
│   │   ├── services/            # Pipeline, Quality, Matching
│   │   ├── config.py            # Pydantic BaseSettings
│   │   └── main.py              # FastAPI Application Entry
├── frontend/                    # Next.js 15 + React + Tailwind CSS Dashboard
├── models/                      # SCRFD & ArcFace ONNX Model Weights
├── data/                        # Biometric Faces, FAISS Index, Logs, SQLite DB
├── scripts/
│   ├── system_check.py          # Environment & Hardware Detection
│   ├── calibrate_threshold.py   # TAR/FAR/FRR Threshold Calibration
│   ├── benchmark.py             # Latency & FPS Performance Profiler
│   └── demo.py                  # One-Click System Launcher
├── tests/                       # Pytest Automated Test Suite
├── docs/                        # Architecture, API, Privacy & Setup Guides
├── requirements.txt             # Python Package Dependencies
└── README.md
```

---

## 🔒 Privacy & Compliance

This software is intended exclusively for authorized educational and classroom identity management.
- Raw video frames are processed in-memory and **never stored permanently**.
- Deleting an individual (`DELETE /persons/{id}`) purges database records, sample images, and removes vectors from the FAISS index.
- Admin APIs require authenticated JWT Bearer tokens.
