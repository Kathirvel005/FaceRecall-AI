import numpy as np
import pytest
from backend.app.ml.recognizer import ArcFaceRecognizer

def test_recognizer_embedding_generation():
    recognizer = ArcFaceRecognizer(model_path="models/w600k_r50.onnx")
    assert recognizer.session is not None

    # Synthetic 112x112 image
    test_face = np.random.randint(50, 200, (112, 112, 3), dtype=np.uint8)
    emb = recognizer.extract_embedding(test_face)

    assert emb.shape == (512,)
    # Verify L2 norm is approximately 1.0
    norm = np.linalg.norm(emb)
    print(f"Embedding shape: {emb.shape}, L2 Norm: {norm:.6f}")
    assert np.isclose(norm, 1.0, atol=1e-4)

    # Test batch extraction
    batch_faces = [test_face, test_face.copy()]
    batch_embs = recognizer.extract_batch(batch_faces)
    assert batch_embs.shape == (2, 512)
    print("Batch embedding shape:", batch_embs.shape)

if __name__ == "__main__":
    test_recognizer_embedding_generation()
