#!/usr/bin/env python3
"""
Model Weights Downloader & Setup Utility.
Ensures SCRFD detection and ArcFace recognition ONNX models are present in models/.
Automatically copies from local insightface cache if present, or downloads from official repository.
"""

import os
import shutil
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_SOURCES = {
    "det_10g.onnx": {
        "local_paths": [
            Path.home() / ".insightface" / "models" / "buffalo_l" / "det_10g.onnx",
        ],
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
    },
    "det_500m.onnx": {
        "local_paths": [
            Path.home() / ".insightface" / "models" / "buffalo_s" / "det_500m.onnx",
        ],
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip"
    },
    "w600k_r50.onnx": {
        "local_paths": [
            Path.home() / ".insightface" / "models" / "buffalo_l" / "w600k_r50.onnx",
        ],
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
    },
    "w600k_mbf.onnx": {
        "local_paths": [
            Path.home() / ".insightface" / "models" / "buffalo_s" / "w600k_mbf.onnx",
        ],
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip"
    }
}

def setup_models():
    print("=" * 60)
    print("      DEEP LEARNING MODEL SETUP & VERIFICATION")
    print("=" * 60)

    for model_name, info in MODEL_SOURCES.items():
        target = MODELS_DIR / model_name
        if target.exists() and target.stat().st_size > 100000:
            print(f"  [OK] {model_name:<16} ({target.stat().st_size / (1024**2):.1f} MB) already exists.")
            continue

        # Check local search paths
        found_local = False
        for loc in info["local_paths"]:
            if loc.exists():
                print(f"  [COPY] Copying {model_name} from local cache: {loc}...")
                shutil.copy2(loc, target)
                found_local = True
                break

        if not found_local:
            print(f"  [INFO] Model {model_name} not found locally.")
            print(f"         Please download the buffalo_l or buffalo_s zip from:")
            print(f"         {info['url']}")

    print("=" * 60)
    print("Model setup check complete.")

if __name__ == "__main__":
    setup_models()
