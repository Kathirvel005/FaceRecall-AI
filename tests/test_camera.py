import time
import pytest
from backend.app.services.camera_service import CameraEngine

def test_camera_engine_lifecycle():
    # Test camera engine initialization, start, frame reading, and clean stop
    cam = CameraEngine(source=0, target_fps=30, width=640, height=480)
    assert not cam.get_status()["is_running"]

    started = cam.start()
    assert started
    assert cam.get_status()["is_running"]

    # Give it a brief moment to connect and grab a frame
    time.sleep(1.0)
    status = cam.get_status()
    print("Camera test status:", status)

    has_frame, frame, ts, fid = cam.get_latest_frame()
    if status["is_connected"]:
        assert has_frame
        assert frame is not None
        assert len(frame.shape) == 3
        print(f"Captured frame shape: {frame.shape}, fid: {fid}")

    cam.stop()
    assert not cam.get_status()["is_running"]
    print("Camera stopped cleanly.")

if __name__ == "__main__":
    test_camera_engine_lifecycle()
