import numpy as np
import cv2
import pytest
from backend.app.ml.alignment import align_face_5pts, ARCFACE_REFERENCE_5PTS

def test_face_alignment():
    # Synthetic face with 5 points rotated by 20 degrees
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Draw reference points shifted and rotated
    pts = ARCFACE_REFERENCE_5PTS * 1.5 + np.array([50.0, 50.0])

    aligned = align_face_5pts(img, pts, output_size=(112, 112))
    assert aligned is not None
    assert aligned.shape == (112, 112, 3)
    print("Alignment test passed. Output shape:", aligned.shape)

if __name__ == "__main__":
    test_face_alignment()
