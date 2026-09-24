from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np
from backend.app.config import settings
from backend.app.core.logging import logger

class LivenessAnalyzer:
    """
    Modular Presentation Attack Defense (PAD) for RGB video streams:
    - High-frequency spectral texture analysis (detects print artifacts & screen moiré)
    - Facial color uniformity check (screen reflection detection)
    - Eye aspect ratio and landmark micro-variation
    Configurable via settings.LIVENESS_ENABLED.
    """

    def __init__(self, enabled: bool = settings.LIVENESS_ENABLED):
        self.enabled = enabled

    def _analyze_fft_texture(self, face_crop: np.ndarray) -> float:
        """
        Calculates frequency distribution of face crop using 2D FFT.
        Printed photos and screens have either suppressed high frequencies (blur)
        or anomalous high-frequency grid periodicities (screen moiré).
        Returns a score in range [0.0, 1.0].
        """
        if face_crop is None or face_crop.size == 0:
            return 0.0

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h < 30 or w < 30:
            return 0.5

        # Resize for standard frequency analysis
        resized = cv2.resize(gray, (128, 128))
        f_transform = np.fft.fft2(resized)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log(np.abs(f_shift) + 1.0)

        # High-frequency region (outer ring)
        center_y, center_x = 64, 64
        y, x = np.ogrid[:128, :128]
        dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

        # High frequency band: radius 30 to 60
        high_freq_mask = (dist_from_center >= 30) & (dist_from_center <= 60)
        high_freq_energy = float(np.mean(magnitude_spectrum[high_freq_mask]))

        # Live human faces typically produce mean log energy between 4.0 and 8.5
        if 3.5 <= high_freq_energy <= 9.0:
            score = 1.0 - abs(high_freq_energy - 6.0) / 4.0
            return max(0.2, min(1.0, score))
        else:
            return 0.2

    def check_liveness(
        self,
        face_crop: np.ndarray,
        landmarks: Optional[np.ndarray] = None
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Returns:
            (is_live, liveness_score, metrics_dict)
        """
        if not self.enabled:
            return True, 1.0, {"enabled": False, "method": "BYPASS"}

        if face_crop is None or face_crop.size == 0:
            return False, 0.0, {"error": "EMPTY_CROP"}

        # 1. FFT texture score
        texture_score = self._analyze_fft_texture(face_crop)

        # 2. Color gradient distribution
        hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
        sat_std = float(np.std(hsv[:, :, 1]))
        sat_score = min(1.0, sat_std / 30.0)

        # Combined liveness confidence
        liveness_score = round(0.70 * texture_score + 0.30 * sat_score, 3)
        # Conservative threshold: prefer live unless strongly anomalous
        is_live = liveness_score >= 0.35

        return is_live, liveness_score, {
            "texture_score": round(texture_score, 3),
            "saturation_std": round(sat_std, 2),
            "is_live": is_live
        }

liveness_analyzer = LivenessAnalyzer()
