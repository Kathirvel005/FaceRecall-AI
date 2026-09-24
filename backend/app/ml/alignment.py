from typing import Optional, Tuple
import cv2
import numpy as np
from backend.app.core.logging import logger

# Canonical 5 reference landmarks for 112x112 ArcFace alignment
ARCFACE_REFERENCE_5PTS = np.array([
    [38.2946, 51.6963],  # left eye
    [73.5318, 51.5014],  # right eye
    [56.0252, 71.7366],  # nose tip
    [41.5493, 92.3655],  # left mouth corner
    [70.7299, 92.2041]   # right mouth corner
], dtype=np.float32)


def align_face_5pts(
    image: np.ndarray,
    landmarks: np.ndarray,
    output_size: Tuple[int, int] = (112, 112)
) -> np.ndarray:
    """
    Perform 2D similarity transformation alignment using the 5 detected facial landmarks.
    Standardized to ArcFace canonical 112x112 coordinates.
    Used identically during REGISTRATION and LIVE RECOGNITION.
    """
    if image is None or image.size == 0:
        return np.zeros((output_size[1], output_size[0], 3), dtype=np.uint8)

    if landmarks is None or len(landmarks) < 5:
        # Fallback to direct resize if no landmarks
        return cv2.resize(image, output_size)

    src_pts = landmarks.astype(np.float32)
    dst_pts = ARCFACE_REFERENCE_5PTS

    if output_size != (112, 112):
        # Scale destination points if output size is different
        scale_x = output_size[0] / 112.0
        scale_y = output_size[1] / 112.0
        dst_pts = dst_pts * np.array([scale_x, scale_y], dtype=np.float32)

    # Estimate similarity transform (rotation + uniform scale + translation, preserving aspect ratio)
    transform_matrix, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts)

    if transform_matrix is None:
        logger.warning("cv2.estimateAffinePartial2D failed; using crop fallback")
        return cv2.resize(image, output_size)

    aligned_face = cv2.warpAffine(
        image,
        transform_matrix,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )
    return aligned_face


def crop_and_align_face(
    image: np.ndarray,
    bbox: list,
    landmarks: Optional[np.ndarray] = None,
    output_size: Tuple[int, int] = (112, 112)
) -> np.ndarray:
    """
    Wrapper that uses 5-point alignment if landmarks are provided,
    otherwise crops bbox with margin and resizes to output_size.
    """
    if landmarks is not None and len(landmarks) >= 5:
        return align_face_5pts(image, landmarks, output_size)

    # Fallback to bbox crop
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))

    if x2 <= x1 or y2 <= y1:
        return np.zeros((output_size[1], output_size[0], 3), dtype=np.uint8)

    crop = image[y1:y2, x1:x2]
    return cv2.resize(crop, output_size)
