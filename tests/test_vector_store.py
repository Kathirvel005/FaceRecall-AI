import numpy as np
import pytest
from backend.app.ml.vector_store import FAISSVectorStore

def test_faiss_vector_store(tmp_path):
    idx_path = str(tmp_path / "test.index")
    meta_path = str(tmp_path / "test_meta.json")

    store = FAISSVectorStore(dimension=512, index_path=idx_path, metadata_path=meta_path)
    assert store.count() == 0

    # Create dummy embeddings
    rng = np.random.RandomState(42)
    vec1 = rng.randn(512).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)

    vec2 = rng.randn(512).astype(np.float32)
    vec2 /= np.linalg.norm(vec2)

    store.add_embedding(vec1, {"student_id": "STU001", "name": "Kathirvel"})
    store.add_embedding(vec2, {"student_id": "STU002", "name": "Arun"})
    assert store.count() == 2

    # Query with exact vec1
    res = store.search(vec1, top_k=2)
    assert len(res) == 2
    assert res[0].name == "Kathirvel"
    assert np.isclose(res[0].similarity, 1.0, atol=1e-3)

    # Test persistence
    store2 = FAISSVectorStore(dimension=512, index_path=idx_path, metadata_path=meta_path)
    assert store2.count() == 2
    res2 = store2.search(vec1, top_k=1)
    assert res2[0].name == "Kathirvel"

    # Test remove
    removed = store2.remove_by_student_id("STU001")
    assert removed == 1
    assert store2.count() == 1
    res3 = store2.search(vec1, top_k=1)
    assert res3[0].name == "Arun"

    print("FAISS vector store passed all tests!")

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        from pathlib import Path
        test_faiss_vector_store(Path(tmp))
