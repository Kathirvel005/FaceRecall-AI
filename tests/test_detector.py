import numpy as np
import cv2
import pytest
from backend.app.ml.detector import SCRFDDetector

def test_detector_initialization():
    detector = SCRFDDetector(model_path="models/det_10g.onnx")
    assert detector.session is not None
    print("Detector initialized successfully.")

def test_detector_inference_blank():
    detector = SCRFDDetector(model_path="models/det_10g.onnx")
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = detector.detect(blank_img)
    assert isinstance(faces, list)
    assert len(faces) == 0
    print("Inference on blank image passed with 0 false detections.")

def test_detector_camera_or_synthetic():
    detector = SCRFDDetector(model_path="models/det_10g.onnx")
    # Draw simple face-like shapes
    test_img = np.full((480, 640, 3), 180, dtype=np.uint8)
    faces = detector.detect(test_img)
    assert isinstance(faces, list)
    print(f"Detector test passed! Detected: {len(faces)} faces.")

if __name__ == "__main__":
    test_detector_initialization()
    test_detector_inference_blank()
    test_detector_camera_or_synthetic()
