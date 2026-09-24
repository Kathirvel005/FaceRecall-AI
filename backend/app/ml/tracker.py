from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from backend.app.config import settings

def calculate_iou(boxA: List[int], boxB: List[int]) -> float:
    """
    Calculate Intersection over Union (IoU) between two boxes [x1, y1, x2, y2].
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return float(iou)


class TrackedFace:
    def __init__(self, track_id: int, bbox: List[int], landmarks: Optional[np.ndarray] = None):
        self.track_id = track_id
        self.bbox = bbox
        self.landmarks = landmarks
        self.hits = 1
        self.age = 1
        self.time_since_update = 0

        # Recognition state
        self.person_id: Optional[str] = None
        self.name: str = "UNKNOWN"
        self.status: str = "UNKNOWN"  # KNOWN, UNKNOWN, LOW_QUALITY
        self.similarity: float = 0.0
        self.quality: float = 0.0
        self.history_names: List[str] = []
        self.history_sims: List[float] = []

    def update(self, bbox: List[int], landmarks: Optional[np.ndarray] = None):
        self.bbox = bbox
        if landmarks is not None:
            self.landmarks = landmarks
        self.hits += 1
        self.age += 1
        self.time_since_update = 0

    def mark_missed(self):
        self.age += 1
        self.time_since_update += 1


class MultiFaceTracker:
    """
    High-Performance Multi-Face Tracker based on IoU and spatial proximity.
    Maintains persistent track IDs across frames and handles occlusion / temporary disappearance.
    """

    def __init__(
        self,
        max_age: int = settings.TRACKER_MAX_AGE,
        min_hits: int = settings.TRACKER_MIN_HITS,
        iou_threshold: float = settings.TRACKER_IOU_THRESHOLD
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: Dict[int, TrackedFace] = {}

    def update(
        self,
        detections: List[Tuple[List[int], Optional[np.ndarray]]],
        is_detection_frame: bool = True
    ) -> List[TrackedFace]:
        """
        Takes list of detected (bbox, landmarks) tuples for current frame.
        Associates detections with existing tracks using IoU matching.
        Returns list of active TrackedFace objects.
        """
        if is_detection_frame:
            for track in self.tracks.values():
                track.mark_missed()

        matched_tracks = set()
        matched_detections = set()

        if len(self.tracks) > 0 and len(detections) > 0:
            track_ids = list(self.tracks.keys())
            iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)

            for t_idx, t_id in enumerate(track_ids):
                for d_idx, (d_box, _) in enumerate(detections):
                    iou_matrix[t_idx, d_idx] = calculate_iou(self.tracks[t_id].bbox, d_box)

            # Greedy bipartite matching
            while True:
                if iou_matrix.size == 0:
                    break
                max_val = np.max(iou_matrix)
                if max_val < self.iou_threshold:
                    break

                t_idx, d_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                t_id = track_ids[t_idx]

                # Update track with matched detection
                box, lmk = detections[d_idx]
                self.tracks[t_id].update(box, lmk)

                matched_tracks.add(t_id)
                matched_detections.add(d_idx)

                # Set row and col to -1 so they won't be matched again
                iou_matrix[t_idx, :] = -1.0
                iou_matrix[:, d_idx] = -1.0

        if is_detection_frame:
            # Create new tracks for unmatched detections
            for d_idx, (d_box, d_lmk) in enumerate(detections):
                if d_idx not in matched_detections:
                    new_track = TrackedFace(track_id=self.next_id, bbox=d_box, landmarks=d_lmk)
                    self.tracks[self.next_id] = new_track
                    self.next_id += 1

        # Prune expired tracks
        dead_ids = [t_id for t_id, track in self.tracks.items() if track.time_since_update > self.max_age]
        for d_id in dead_ids:
            del self.tracks[d_id]

        # Return active tracks visible in current frame
        active_tracks = [t for t in self.tracks.values() if t.time_since_update <= 2]
        return active_tracks
