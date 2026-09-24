#!/usr/bin/env python3
"""
System Environment and Hardware Detector
Detects CPU, RAM, NVIDIA GPU, CUDA, OpenCV, Python, and ONNX Runtime execution providers.
Automatically determines the optimal execution provider (CUDA vs CPU).
"""

import sys
import platform
import subprocess
import shutil

def get_cpu_info():
    try:
        import psutil
        cpu_name = platform.processor() or "Unknown CPU"
        cores_logical = psutil.cpu_count(logical=True)
        cores_physical = psutil.cpu_count(logical=False)
        return f"{cpu_name} ({cores_physical} physical, {cores_logical} logical cores)"
    except Exception:
        return platform.processor() or "Unknown CPU"

def get_ram_info():
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        available_gb = mem.available / (1024 ** 3)
        return f"{total_gb:.2f} GB Total ({available_gb:.2f} GB Available)"
    except Exception:
        return "Unknown RAM"

def get_gpu_info():
    gpu_info = {
        "name": "None",
        "cuda_available": False,
        "vram_total_mb": 0,
        "vram_free_mb": 0,
        "driver_version": "N/A"
    }

    if shutil.which("nvidia-smi"):
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = res.stdout.strip()
            if output:
                lines = output.splitlines()
                first_gpu = lines[0].split(",")
                gpu_info["name"] = first_gpu[0].strip()
                gpu_info["driver_version"] = first_gpu[1].strip()
                gpu_info["vram_total_mb"] = int(first_gpu[2].strip())
                gpu_info["vram_free_mb"] = int(first_gpu[3].strip())
                gpu_info["cuda_available"] = True
        except Exception:
            pass

    return gpu_info

def get_opencv_info():
    try:
        import cv2
        return cv2.__version__
    except ImportError:
        return "Not Installed"

def get_onnx_info(prefer_cuda: bool = True):
    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        selected_provider = "CPUExecutionProvider"

        if prefer_cuda and "CUDAExecutionProvider" in available_providers:
            selected_provider = "CUDAExecutionProvider"
        elif "CPUExecutionProvider" in available_providers:
            selected_provider = "CPUExecutionProvider"
        elif available_providers:
            selected_provider = available_providers[0]

        return {
            "version": ort.__version__,
            "available_providers": available_providers,
            "selected_provider": selected_provider
        }
    except ImportError:
        return {
            "version": "Not Installed",
            "available_providers": [],
            "selected_provider": "None"
        }

def inspect_environment():
    gpu = get_gpu_info()
    cpu = get_cpu_info()
    ram = get_ram_info()
    cv2_ver = get_opencv_info()
    onnx = get_onnx_info(prefer_cuda=gpu["cuda_available"])

    report = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": cpu,
        "ram": ram,
        "gpu_name": gpu["name"],
        "cuda_available": gpu["cuda_available"],
        "vram": f"{gpu['vram_total_mb']} MB (Free: {gpu['vram_free_mb']} MB)" if gpu['vram_total_mb'] else "N/A",
        "opencv_version": cv2_ver,
        "onnx_version": onnx["version"],
        "onnx_available_providers": onnx["available_providers"],
        "onnx_selected_provider": onnx["selected_provider"]
    }
    return report

def main():
    print("=" * 60)
    print("   ADVANCED MULTI-FACE SYSTEM - HARDWARE & ENVIRONMENT")
    print("=" * 60)
    info = inspect_environment()
    print(f"Python:             {info['python_version']} ({info['platform']})")
    print(f"CPU:                {info['cpu']}")
    print(f"RAM:                {info['ram']}")
    print(f"GPU:                {info['gpu_name']}")
    print(f"CUDA:               {'Available' if info['cuda_available'] else 'Unavailable'}")
    print(f"VRAM:               {info['vram']}")
    print(f"OpenCV:             {info['opencv_version']}")
    print(f"ONNX Runtime:       {info['onnx_version']}")
    print(f"Available Providers:{', '.join(info['onnx_available_providers'])}")
    print(f"Selected Provider:  {info['onnx_selected_provider']}")
    print("=" * 60)
    if info['onnx_selected_provider'] == "CUDAExecutionProvider":
        print("[SUCCESS] High-Performance GPU Acceleration is ACTIVE via CUDAExecutionProvider.")
    else:
        print("[INFO] CPU Execution Provider is active. System will run robustly in CPU fallback mode.")
    print("=" * 60)

if __name__ == "__main__":
    main()
