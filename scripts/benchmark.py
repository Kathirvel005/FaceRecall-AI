#!/usr/bin/env python3
"""
Performance and Latency Benchmark Tool
Measures multi-face detection latency, ArcFace embedding latency, total pipeline FPS,
p95 latency, CPU utilization, and GPU VRAM usage.
"""

import sys
import time
import psutil
import numpy as np

from backend.app.config import settings
from backend.app.ml.detector import SCRFDDetector
from backend.app.ml.recognizer import ArcFaceRecognizer
from backend.app.ml.vector_store import FAISSVectorStore
from scripts.system_check import get_gpu_info

def run_benchmark(num_warmup: int = 10, num_iterations: int = 50, test_face_counts: list = [1, 5, 10]):
    print("=" * 70)
    print("      REAL-TIME MULTI-FACE RECOGNITION SYSTEM BENCHMARK")
    print("=" * 70)

    gpu = get_gpu_info()
    print(f"Device:           {'CUDA (' + gpu['name'] + ')' if gpu['cuda_available'] else 'CPU'}")
    print(f"Detector Model:   {settings.DETECTION_MODEL_PATH}")
    print(f"Recognizer Model: {settings.RECOGNITION_MODEL_PATH}")
    print(f"Iterations:       {num_iterations} runs per scenario")
    print("-" * 70)

    detector = SCRFDDetector()
    recognizer = ArcFaceRecognizer()
    store = FAISSVectorStore()

    # Pre-populate FAISS with 50 registered identities for realistic search benchmark
    rng = np.random.RandomState(42)
    sample_vecs = rng.randn(100, 512).astype(np.float32)
    sample_vecs /= np.linalg.norm(sample_vecs, axis=1, keepdims=True)
    sample_metas = [{"student_id": f"STU_{i:03d}", "name": f"Student {i}"} for i in range(100)]
    store.rebuild(sample_vecs, sample_metas)

    # Warmup
    dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    for _ in range(num_warmup):
        _ = detector.detect(dummy_frame)
        _ = recognizer.extract_embedding(np.zeros((112, 112, 3), dtype=np.uint8))

    # 1. Detection Benchmark (single frame 1280x720)
    det_latencies = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        _ = detector.detect(dummy_frame)
        det_latencies.append((time.perf_counter() - t0) * 1000.0)

    det_avg = np.mean(det_latencies)
    det_p95 = np.percentile(det_latencies, 95)
    det_fps = 1000.0 / det_avg

    print(f"Detection Latency (720p):  Avg: {det_avg:6.2f} ms | P95: {det_p95:6.2f} ms | {det_fps:5.1f} FPS")

    # 2. Recognition & Embedding Benchmark per Face
    rec_latencies = []
    dummy_crop = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        _ = recognizer.extract_embedding(dummy_crop)
        rec_latencies.append((time.perf_counter() - t0) * 1000.0)

    rec_avg = np.mean(rec_latencies)
    rec_p95 = np.percentile(rec_latencies, 95)
    rec_fps = 1000.0 / rec_avg
    print(f"ArcFace Latency (per face): Avg: {rec_avg:6.2f} ms | P95: {rec_p95:6.2f} ms | {rec_fps:5.1f} FPS")

    # 3. Vector DB Search Benchmark (100 items)
    dummy_query = rng.randn(512).astype(np.float32)
    dummy_query /= np.linalg.norm(dummy_query)
    search_latencies = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        _ = store.search(dummy_query, top_k=5)
        search_latencies.append((time.perf_counter() - t0) * 1000.0)

    search_avg = np.mean(search_latencies)
    print(f"FAISS Search Latency:       Avg: {search_avg:6.3f} ms")

    # 4. Multi-Face Scenarios (End-to-End Pipeline simulation)
    print("-" * 70)
    print(f"{'Simultaneous Faces':<20} | {'Total Latency':<15} | {'Pipeline FPS':<14} | {'Status'}")
    print("-" * 70)

    for n_faces in test_face_counts:
        # Simulate pipeline: 1 detection + N recognition passes + N FAISS queries
        total_time_ms = det_avg + (n_faces * rec_avg) + (n_faces * search_avg)
        pipeline_fps = 1000.0 / total_time_ms
        status = "REAL-TIME (>= 15 FPS)" if pipeline_fps >= 15 else "ACCEPTABLE"
        print(f"{n_faces:<20} | {total_time_ms:6.2f} ms       | {pipeline_fps:5.1f} FPS       | {status}")

    print("=" * 70)
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    print("SYSTEM RESOURCE UTILIZATION:")
    print(f"  CPU Utilization:    {cpu_percent:.1f}%")
    print(f"  RAM Utilization:    {mem.percent:.1f}% ({mem.used / (1024**3):.2f} GB used)")
    if gpu["cuda_available"]:
        gpu_latest = get_gpu_info()
        print(f"  GPU Name:           {gpu_latest['name']}")
        print(f"  GPU VRAM Usage:     {gpu_latest['vram_total_mb'] - gpu_latest['vram_free_mb']} MB / {gpu_latest['vram_total_mb']} MB")
    print("=" * 70)

if __name__ == "__main__":
    run_benchmark(num_warmup=5, num_iterations=20)
