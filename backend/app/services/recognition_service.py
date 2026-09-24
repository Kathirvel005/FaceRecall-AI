import time
import datetime
import asyncio
import base64
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import cv2
import numpy as np

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.ml.detector import SCRFDDetector, DetectedFace
from backend.app.ml.recognizer import ArcFaceRecognizer, face_recognizer
from backend.app.ml.alignment import align_face_5pts, crop_and_align_face
from backend.app.ml.tracker import MultiFaceTracker, TrackedFace
from backend.app.ml.vector_store import FAISSVectorStore, vector_store, SearchResult
from backend.app.services.quality_service import FaceQualityAnalyzer, quality_analyzer
from backend.app.services.matching_service import IdentityMatcher, identity_matcher, MatchDecision
from backend.app.services.tracking_service import TemporalSmoothingManager, temporal_smoother
from backend.app.services.liveness_service import LivenessAnalyzer, liveness_analyzer
from backend.app.services.camera_service import CameraEngine, camera_engine
from backend.app.schemas.recognition import FaceRecognitionResult, RecognitionFrameSummary, QualityMetrics

class RecognitionPipeline:
    """
    Real-Time Multi-Face Processing Pipeline:
    Camera -> Detection -> Tracking -> Quality -> ArcFace -> FAISS -> Temporal Voting -> WebSocket
    """

    def __init__(
        self,
        camera: Optional[CameraEngine] = None,
        detector: Optional[SCRFDDetector] = None,
        recognizer: Optional[ArcFaceRecognizer] = None,
        store: Optional[FAISSVectorStore] = None,
        detection_interval: int = settings.DETECTION_INTERVAL,
        recognition_interval: int = settings.RECOGNITION_INTERVAL
    ):
        self.camera = camera or camera_engine
        self.detector = detector or SCRFDDetector()
        self.recognizer = recognizer or face_recognizer
        self.store = store or vector_store
        self.tracker = MultiFaceTracker()
        self.smoother = temporal_smoother

        self.detection_interval = detection_interval
        self.recognition_interval = recognition_interval

        self._is_active = False
        self._loop_task: Optional[asyncio.Task] = None
        self._subscribers: Set[asyncio.Queue] = set()

        self.frame_count = 0
        self.last_latency_ms = 0.0
        self.fps_meter = 0.0

        # Cache of latest recognition summary for REST endpoints
        self.latest_summary: Optional[RecognitionFrameSummary] = None

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=10)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)

    async def _broadcast(self, summary: RecognitionFrameSummary):
        self.latest_summary = summary
        dead_queues = []
        for q in self._subscribers:
            try:
                if q.full():
                    # Drop oldest if consumer is slow
                    _ = q.get_nowait()
                q.put_nowait(summary)
            except Exception:
                dead_queues.append(q)
        for dq in dead_queues:
            self._subscribers.discard(dq)

    def process_frame(self, frame: np.ndarray, timestamp: float, frame_id: int) -> RecognitionFrameSummary:
        start_time = time.perf_counter()
        self.frame_count += 1
        h, w = frame.shape[:2]

        # 1. Detection (Run every detection_interval frames to save compute)
        should_detect = (self.frame_count % self.detection_interval == 0) or (len(self.tracker.tracks) == 0)
        detections: List[Tuple[List[int], Optional[np.ndarray]]] = []

        if should_detect:
            detected_faces = self.detector.detect(frame)
            for df in detected_faces:
                detections.append((df.bbox, df.landmarks))

        # 2. Tracking: Update multi-face tracker
        active_tracks = self.tracker.update(detections, is_detection_frame=should_detect)
        active_track_ids = [t.track_id for t in active_tracks]
        self.smoother.cleanup_old_tracks(active_track_ids)

        faces_results: List[FaceRecognitionResult] = []
        known_count = 0
        unknown_count = 0

        # 3. Recognition & Quality Verification for each active track
        for track in active_tracks:
            bbox = track.bbox
            landmarks = track.landmarks

            # Compute quality
            quality = quality_analyzer.analyze(
                frame=frame,
                bbox=bbox,
                landmarks=landmarks if landmarks is not None else np.zeros((5, 2)),
                detection_conf=1.0
            )

            # Determine whether to run heavy ArcFace embedding
            needs_recognition = (
                (self.frame_count % self.recognition_interval == 0) or
                (track.status == "VERIFYING") or
                (track.hits <= 2)
            )

            if needs_recognition and quality.is_valid and landmarks is not None:
                # 4. Alignment
                aligned = align_face_5pts(frame, landmarks)

                # 5. ArcFace Feature Embedding
                embedding = self.recognizer.extract_embedding(aligned)

                # 6. FAISS Nearest Neighbor Search
                candidates = self.store.search(embedding, top_k=settings.TOP_K_CANDIDATES)

                # 7. Identity Matching with Guardrails
                decision = identity_matcher.match(candidates, quality)

                # 8. Liveness check
                crop = frame[max(0, bbox[1]):min(h, bbox[3]), max(0, bbox[0]):min(w, bbox[2])]
                is_live, liveness_score, _ = liveness_analyzer.check_liveness(crop, landmarks)

                # 9. Temporal Smoothing
                conf_pid, conf_name, conf_status, avg_sim, avg_q = self.smoother.update_track(
                    track.track_id, decision, quality.quality_score
                )

                track.person_id = conf_pid
                track.name = conf_name
                track.status = conf_status
                track.similarity = avg_sim
                track.quality = avg_q

            # Compile result for UI
            status = track.status
            name = track.name
            sim = track.similarity

            if status == "KNOWN":
                known_count += 1
            elif status == "UNKNOWN":
                unknown_count += 1

            faces_results.append(FaceRecognitionResult(
                track_id=track.track_id,
                person_id=track.person_id,
                name=name,
                status=status,
                similarity=round(sim, 3),
                quality=round(quality.quality_score, 3),
                bbox=bbox,
                landmarks=landmarks.round(1).tolist() if landmarks is not None else None,
                is_live=True,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            ))

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        self.last_latency_ms = round(latency_ms, 2)

        summary = RecognitionFrameSummary(
            frame_id=frame_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            camera_id=self.camera.camera_id,
            fps=self.camera.get_status().get("current_fps", 30.0),
            face_count=len(faces_results),
            known_count=known_count,
            unknown_count=unknown_count,
            inference_latency_ms=self.last_latency_ms,
            frame_width=w,
            frame_height=h,
            faces=faces_results
        )
        return summary

    async def _run_loop(self):
        logger.info("Starting Real-Time Recognition Pipeline loop...")
        self._is_active = True

        if not self.camera.get_status()["is_running"]:
            self.camera.start()

        while self._is_active:
            has_frame, frame, ts, fid = self.camera.get_latest_frame()
            if not has_frame or frame is None:
                await asyncio.sleep(0.01)
                continue

            summary = self.process_frame(frame, ts, fid)
            await self._broadcast(summary)

            # Yield control to event loop
            await asyncio.sleep(0.005)

        logger.info("Real-Time Recognition Pipeline loop ended.")

    def start(self):
        if self._is_active:
            return
        self._is_active = True
        self._loop_task = asyncio.create_task(self._run_loop())

    def stop(self):
        self._is_active = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None

pipeline = RecognitionPipeline()
