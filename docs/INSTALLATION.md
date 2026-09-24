# Installation & Deployment Guide

## Prerequisites

- **Operating System:** Windows 10/11 or Linux (Ubuntu 20.04/22.04 LTS)
- **Python:** 3.10 to 3.13 (Python 3.13 recommended)
- **Node.js:** v18.0.0 or higher (v24.x recommended)
- **Camera:** Built-in webcam, USB webcam, or RTSP network camera
- **Optional GPU:** NVIDIA GeForce / RTX GPU with CUDA support for accelerated inference

---

## Step 1: Clone or Open Repository

```bash
cd "d:\Project work\Full stack project\Cam Related"
```

## Step 2: Python Environment Setup

```powershell
# Create Python virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt
```

## Step 3: Verify Hardware & Execution Providers

Run the system hardware detector:

```powershell
python scripts/system_check.py
```

Expected output confirms CPU, RAM, OpenCV, and ONNX Runtime providers.

## Step 4: Model Verification

Verify that ONNX model weights exist in `models/`:
- `models/det_10g.onnx` (SCRFD Face Detector)
- `models/w600k_r50.onnx` (ArcFace Feature Recognizer)

## Step 5: Database Initialization & Automated Tests

```powershell
# Run the complete automated test suite
$env:PYTHONPATH="."
pytest tests/ -v
```

## Step 6: Start Backend Server

```powershell
# Start FastAPI backend with Uvicorn
$env:PYTHONPATH="."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at:
- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- WebSocket Feed: `ws://localhost:8000/ws/recognition`

## Step 7: Start Next.js Frontend Dashboard

```powershell
cd frontend
npm install
npm run dev
```

Frontend will be available at:
- Web Dashboard: `http://localhost:3000`

## Step 8: One-Click Demo Mode

To launch the complete integrated system in demo mode:

```powershell
python scripts/demo.py
```
