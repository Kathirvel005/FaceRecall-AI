import time
import threading
from typing import Optional, Tuple, Dict, Any, Union
import cv2
import numpy as np
from backend.app.config import settings
from backend.app.core.logging import logger

class CameraEngine:
    """
    Robust Camera Subsystem with separate capture thread, automatic reconnect,
    frame-dropping when processing is slow, and support for Webcams, USB, IP, and RTSP streams.
    """

    def __init__(
        self,
        source: Union[int, str] = 0,
        target_fps: int = 30,
        width: int = 1280,
        height: int = 720,
        reconnect_interval_sec: float = 2.0,
        max_reconnect_attempts: int = 10,
        camera_id: str = "default_cam"
    ):
        self.camera_id = camera_id
        # Convert numeric strings to int (e.g. "0" -> 0)
        if isinstance(source, str) and source.strip().isdigit():
            self.source = int(source.strip())
        else:
            self.source = source

        self.target_fps = target_fps
        self.width = width
        self.height = height
        self.reconnect_interval_sec = reconnect_interval_sec
        self.max_reconnect_attempts = max_reconnect_attempts

        self.cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._lock = threading.Lock()

        # Frame buffer (always contains latest frame for zero-latency pipeline)
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_timestamp: float = 0.0
        self._frame_id: int = 0
        self._dropped_frames: int = 0

        # Performance monitoring
        self._fps_counter: int = 0
        self._fps_last_time: float = time.time()
        self._current_fps: float = 0.0
        self._is_connected: bool = False
        self._last_error: Optional[str] = None

    def _open_capture(self) -> bool:
        try:
            if self.cap is not None:
                self.cap.release()

            logger.info(f"Opening camera source: {self.source} ({self.camera_id})...")
            # For Windows webcams, CAP_DSHOW often opens much faster without long delay
            if isinstance(self.source, int):
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.source)
            else:
                self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                self._is_connected = False
                self._last_error = f"Failed to open video source: {self.source}"
                logger.error(self._last_error)
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Query actual resolution
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Camera opened successfully: {actual_w}x{actual_h} @ target {self.target_fps} FPS")

            self._is_connected = True
            self._last_error = None
            return True
        except Exception as e:
            self._is_connected = False
            self._last_error = str(e)
            logger.error(f"Error opening camera source {self.source}: {e}")
            return False

    def _capture_loop(self):
        reconnect_count = 0
        while self._running:
            if not self._is_connected or self.cap is None or not self.cap.isOpened():
                if reconnect_count >= self.max_reconnect_attempts:
                    logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached for camera {self.source}.")
                    time.sleep(self.reconnect_interval_sec)
                    reconnect_count = 0  # Continue backing off

                logger.warning(f"Attempting camera reconnection ({reconnect_count + 1}/{self.max_reconnect_attempts})...")
                success = self._open_capture()
                if not success:
                    reconnect_count += 1
                    time.sleep(self.reconnect_interval_sec)
                    continue
                else:
                    reconnect_count = 0

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.warning("Failed to grab frame from camera. Triggering reconnection...")
                self._is_connected = False
                time.sleep(0.5)
                continue

            current_time = time.time()

            # Atomic update of latest frame (old frame automatically discarded = frame dropping)
            with self._lock:
                if self._latest_frame is not None:
                    self._dropped_frames += 1
                self._latest_frame = frame
                self._latest_timestamp = current_time
                self._frame_id += 1

            # FPS calculation
            self._fps_counter += 1
            elapsed = current_time - self._fps_last_time
            if elapsed >= 1.0:
                self._current_fps = round(self._fps_counter / elapsed, 2)
                self._fps_counter = 0
                self._fps_last_time = current_time

            # Small sleep to prevent thread thrashing if source is running fast
            time.sleep(0.001)

        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self._is_connected = False
        logger.info(f"Camera capture thread terminated cleanly for source: {self.source}")

    def start(self) -> bool:
        with self._lock:
            if self._running:
                logger.warning("Camera engine is already running.")
                return True

            self._running = True
            if not self._open_capture():
                logger.warning("Initial camera capture open failed; capture thread will attempt auto-reconnect.")

            self._thread = threading.Thread(target=self._capture_loop, name=f"CameraCapture-{self.camera_id}", daemon=True)
            self._thread.start()
            logger.info("Camera engine thread started.")
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            logger.info("Stopping camera engine...")
            self._running = False

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Camera engine stopped.")

    def get_latest_frame(self) -> Tuple[bool, Optional[np.ndarray], float, int]:
        """
        Returns:
            (has_frame, frame, timestamp, frame_id)
        """
        with self._lock:
            if self._latest_frame is None:
                return False, None, 0.0, self._frame_id
            # Return copy or reference
            return True, self._latest_frame.copy(), self._latest_timestamp, self._frame_id

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "source": str(self.source),
                "is_running": self._running,
                "is_connected": self._is_connected,
                "current_fps": self._current_fps,
                "target_fps": self.target_fps,
                "resolution": f"{self.width}x{self.height}",
                "total_frames": self._frame_id,
                "dropped_frames": self._dropped_frames,
                "last_error": self._last_error
            }


# Global default camera instance for system
camera_engine = CameraEngine(
    source=settings.DEFAULT_CAMERA_INDEX,
    target_fps=settings.CAMERA_FPS,
    width=settings.CAMERA_WIDTH,
    height=settings.CAMERA_HEIGHT
)
