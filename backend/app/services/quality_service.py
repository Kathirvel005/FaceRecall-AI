from typing import Dict, Any, List, Optional, Tuple
import math
import cv2
import numpy as np
from backend.app.config import settings
from backend.app.schemas.recognition import QualityMetrics
from backend.app.core.logging import logger

class FaceQualityAnalyzer:
    """
    Comprehensive Face Quality Evaluator:
    - Size check
    - Sharpness / Blur detection (Laplacian variance)
    - Brightness analysis (mean intensity)
    - 3D-Pose estimation from 5 landmarks (Yaw, Pitch, Roll)
    - Composite quality score [0.0 - 1.0]
    """

    def __init__(
        self,
        min_size: int = settings.MIN_FACE_SIZE,
        blur_threshold: float = settings.BLUR_THRESHOLD,
        min_brightness: float = settings.MIN_BRIGHTNESS,
        max_brightness: float = settings.MAX_BRIGHTNESS,
        max_yaw: float = settings.MAX_YAW_DEG,
        max_pitch: float = settings.MAX_PITCH_DEG,
        min_quality_score: float = settings.MIN_QUALITY_SCORE
    ):
        self.min_size = min_size
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.max_yaw = max_yaw
        self.max_pitch = max_pitch
        self.min_quality_score = min_quality_score

    def estimate_pose(self, landmarks: np.ndarray) -> Tuple[float, float, float]:
        """
        Estimate Yaw, Pitch, Roll angles in degrees from 5 landmarks:
        0: left eye, 1: right eye, 2: nose, 3: left mouth corner, 4: right mouth corner
        """
        if landmarks is None or len(landmarks) < 5:
            return 0.0, 0.0, 0.0

        p0 = landmarks[0]  # left eye
        p1 = landmarks[1]  # right eye
        p2 = landmarks[2]  # nose
        p3 = landmarks[3]  # left mouth
        p4 = landmarks[4]  # right mouth

        # 1. Roll: Angle between eyes
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        roll = math.degrees(math.atan2(dy, dx))

        # 2. Yaw: Ratio of nose distance to left eye vs right eye
        dist_left = np.linalg.norm(p2 - p0)
        dist_right = np.linalg.norm(p2 - p1)
        total_dist = dist_left + dist_right
        if total_dist > 1e-4:
            ratio = (dist_left - dist_right) / total_dist
            # ratio of 0 -> frontal (0 deg). ratio of +0.5 -> ~45 deg
            yaw = float(ratio * 90.0)
        else:
            yaw = 0.0

        # 3. Pitch: Vertical ratio of nose between eye line and mouth line
        eye_mid = (p0 + p1) / 2.0
        mouth_mid = (p3 + p4) / 2.0
        face_v_span = mouth_mid[1] - eye_mid[1]

        if face_v_span > 1e-4:
            nose_v_ratio = (p2[1] - eye_mid[1]) / face_v_span
            # Canonical frontal nose sits at ~0.55 of the span
            pitch = float((nose_v_ratio - 0.55) * 80.0)
        else:
            pitch = 0.0

        return round(yaw, 2), round(pitch, 2), round(roll, 2)

    def analyze(
        self,
        frame: np.ndarray,
        bbox: List[int],
        landmarks: np.ndarray,
        detection_conf: float
    ) -> QualityMetrics:
        """
        Analyze face quality and return detailed QualityMetrics.
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))

        fw = x2 - x1
        fh = y2 - y1
        face_size = min(fw, fh)

        if fw <= 10 or fh <= 10:
            return QualityMetrics(
                face_size=face_size,
                sharpness=0.0,
                brightness=0.0,
                yaw=0.0,
                pitch=0.0,
                detection_conf=detection_conf,
                is_valid=False,
                quality_score=0.0,
                reason="FACE_TOO_SMALL"
            )

        face_crop = frame[y1:y2, x1:x2]
        gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

        # 1. Sharpness / Blur
        laplacian_var = float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())

        # 2. Brightness
        mean_brightness = float(np.mean(gray_crop))

        # 3. Pose
        yaw, pitch, roll = self.estimate_pose(landmarks)

        # Quality scoring components (each 0.0 to 1.0)
        # Size score: 60px -> 0.4, 150px+ -> 1.0
        size_score = min(1.0, max(0.0, (face_size - 30) / 120.0))

        # Sharpness score: 50 -> 0.5, 150+ -> 1.0
        sharpness_score = min(1.0, max(0.0, laplacian_var / 150.0))

        # Brightness score: optimal 120-150
        if 40.0 <= mean_brightness <= 220.0:
            # Distance from center 130
            b_diff = abs(mean_brightness - 130.0)
            brightness_score = max(0.0, 1.0 - (b_diff / 110.0))
        else:
            brightness_score = 0.1

        # Pose score: 0 deg -> 1.0, 35 deg -> 0.3
        pose_penalty = (abs(yaw) / 45.0) * 0.6 + (abs(pitch) / 40.0) * 0.4
        pose_score = max(0.0, min(1.0, 1.0 - pose_penalty))

        # Composite quality score
        composite_score = (
            0.20 * size_score +
            0.30 * sharpness_score +
            0.15 * brightness_score +
            0.15 * pose_score +
            0.20 * min(1.0, max(0.0, detection_conf))
        )
        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        # Rejection reasons
        reason = None
        is_valid = True

        if face_size < self.min_size:
            is_valid = False
            reason = f"TOO_SMALL ({face_size}px < {self.min_size}px)"
        elif laplacian_var < self.blur_threshold:
            is_valid = False
            reason = f"BLURRED (sharpness {laplacian_var:.1f} < {self.blur_threshold})"
        elif mean_brightness < self.min_brightness:
            is_valid = False
            reason = f"UNDEREXPOSED ({mean_brightness:.1f} < {self.min_brightness})"
        elif mean_brightness > self.max_brightness:
            is_valid = False
            reason = f"OVEREXPOSED ({mean_brightness:.1f} > {self.max_brightness})"
        elif abs(yaw) > self.max_yaw:
            is_valid = False
            reason = f"EXTREME_YAW ({abs(yaw):.1f}° > {self.max_yaw}°)"
        elif abs(pitch) > self.max_pitch:
            is_valid = False
            reason = f"EXTREME_PITCH ({abs(pitch):.1f}° > {self.max_pitch}°)"
        elif composite_score < self.min_quality_score:
            is_valid = False
            reason = f"LOW_QUALITY_SCORE ({composite_score:.2f} < {self.min_quality_score})"

        return QualityMetrics(
            face_size=face_size,
            sharpness=round(laplacian_var, 2),
            brightness=round(mean_brightness, 2),
            yaw=yaw,
            pitch=pitch,
            detection_conf=round(detection_conf, 3),
            is_valid=is_valid,
            quality_score=composite_score,
            reason=reason
        )

quality_analyzer = FaceQualityAnalyzer()
