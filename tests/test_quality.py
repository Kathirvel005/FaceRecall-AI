import numpy as np
import cv2
import pytest
from backend.app.services.quality_service import FaceQualityAnalyzer

def test_quality_analysis():
    analyzer = FaceQualityAnalyzer()

    # Create dummy sharp face image with texture
    test_img = np.random.randint(50, 200, (300, 300, 3), dtype=np.uint8)
    bbox = [50, 50, 250, 250]
    # Landmarks for frontal face: left eye, right eye, nose, left mouth, right mouth
    landmarks = np.array([
        [100.0, 110.0],
        [200.0, 110.0],
        [150.0, 160.0],
        [110.0, 210.0],
        [190.0, 210.0]
    ], dtype=np.float32)

    res = analyzer.analyze(test_img, bbox, landmarks, 0.95)
    print("Sharp textured face quality:", res)
    assert res.face_size == 200
    assert res.sharpness > 50.0
    assert abs(res.yaw) < 10.0

    # Test blurred face
    blurred_img = cv2.GaussianBlur(test_img, (31, 31), 10.0)
    res_blurred = analyzer.analyze(blurred_img, bbox, landmarks, 0.95)
    print("Blurred face quality:", res_blurred)
    assert not res_blurred.is_valid
    assert "BLURRED" in (res_blurred.reason or "")

    # Test small face
    small_bbox = [50, 50, 80, 80]
    res_small = analyzer.analyze(test_img, small_bbox, landmarks, 0.95)
    print("Small face quality:", res_small)
    assert not res_small.is_valid
    assert "TOO_SMALL" in (res_small.reason or "")

if __name__ == "__main__":
    test_quality_analysis()
