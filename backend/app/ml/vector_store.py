from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import threading
import numpy as np
import faiss

from backend.app.config import settings
from backend.app.core.logging import logger

class SearchResult:
    def __init__(self, person_id: str, name: str, similarity: float, metadata: Dict[str, Any]):
        self.person_id = person_id
        self.name = name
        self.similarity = float(similarity)
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "name": self.name,
            "similarity": round(self.similarity, 4),
            "metadata": self.metadata
        }


class FAISSVectorStore:
    """
    FAISS-based vector database with cosine similarity (Inner Product on L2-normalized vectors).
    Maintains persistent index and synchronized metadata store.
    Supports atomic add, remove, search, rebuild, save, and load.
    """

    def __init__(
        self,
        dimension: int = settings.EMBEDDING_DIM,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None
    ):
        self.dimension = dimension
        self.index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self.metadata_path = Path(metadata_path or settings.METADATA_STORE_PATH)

        self._lock = threading.RLock()
        self.index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.dimension)
        self.metadata_records: List[Dict[str, Any]] = []

        self._ensure_storage_dirs()
        self.load()

    def _ensure_storage_dirs(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def count(self) -> int:
        with self._lock:
            return self.index.ntotal

    def add_embedding(self, vector: np.ndarray, metadata: Dict[str, Any]) -> int:
        """
        Add a single L2-normalized 512-D embedding with metadata.
        """
        with self._lock:
            vec = vector.astype(np.float32).reshape(1, self.dimension)
            norm = np.linalg.norm(vec)
            if not np.isclose(norm, 1.0, atol=1e-3):
                vec = vec / (norm + 1e-10)

            self.index.add(vec)
            self.metadata_records.append(metadata)
            idx = len(self.metadata_records) - 1
            self.save()
            return idx

    def add_batch(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        """
        Add a batch of embeddings and metadatas.
        """
        with self._lock:
            if len(vectors) == 0:
                return

            vecs = vectors.astype(np.float32).reshape(-1, self.dimension)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs = vecs / (norms + 1e-10)

            self.index.add(vecs)
            self.metadata_records.extend(metadatas)
            self.save()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """
        Perform nearest neighbor cosine similarity search.
        Returns top_k SearchResult objects sorted by similarity descending.
        """
        with self._lock:
            if self.index.ntotal == 0:
                return []

            vec = query_vector.astype(np.float32).reshape(1, self.dimension)
            norm = np.linalg.norm(vec)
            if not np.isclose(norm, 1.0, atol=1e-3):
                vec = vec / (norm + 1e-10)

            k = min(top_k, self.index.ntotal)
            similarities, indices = self.index.search(vec, k)

            results: List[SearchResult] = []
            for sim, idx in zip(similarities[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata_records):
                    continue
                meta = self.metadata_records[idx]
                results.append(SearchResult(
                    person_id=str(meta.get("student_id", meta.get("person_id", "UNKNOWN"))),
                    name=str(meta.get("name", "UNKNOWN")),
                    similarity=float(sim),
                    metadata=meta
                ))

            return results

    def remove_by_student_id(self, student_id: str) -> int:
        """
        Remove all embeddings belonging to student_id and rebuild index.
        """
        with self._lock:
            initial_count = len(self.metadata_records)
            keep_indices = []
            for i, meta in enumerate(self.metadata_records):
                sid = str(meta.get("student_id", meta.get("person_id", "")))
                if sid != str(student_id):
                    keep_indices.append(i)

            removed_count = initial_count - len(keep_indices)
            if removed_count == 0:
                return 0

            if len(keep_indices) == 0:
                # Clear all
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata_records = []
            else:
                # Reconstruct remaining vectors and rebuild index
                remaining_vecs = np.zeros((len(keep_indices), self.dimension), dtype=np.float32)
                for new_pos, old_idx in enumerate(keep_indices):
                    vec = self.index.reconstruct(int(old_idx))
                    remaining_vecs[new_pos] = vec

                new_metas = [self.metadata_records[i] for i in keep_indices]

                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(remaining_vecs)
                self.metadata_records = new_metas

            self.save()
            logger.info(f"Removed {removed_count} embeddings for student_id={student_id}. Remaining: {self.index.ntotal}")
            return removed_count

    def rebuild(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        """
        Completely reset and rebuild index from fresh records.
        """
        with self._lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata_records = []
            if len(vectors) > 0:
                self.add_batch(vectors, metadatas)
            else:
                self.save()
            logger.info(f"FAISS index rebuilt successfully with {self.index.ntotal} vectors.")

    def save(self) -> None:
        """
        Persist FAISS index binary and metadata JSON to disk.
        """
        with self._lock:
            try:
                faiss.write_index(self.index, str(self.index_path))
                with open(self.metadata_path, "w", encoding="utf-8") as f:
                    json.dump(self.metadata_records, f, indent=2)
                logger.debug(f"Saved FAISS index ({self.index.ntotal} items) to disk.")
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")

    def load(self) -> bool:
        """
        Load FAISS index binary and metadata JSON from disk if they exist.
        """
        with self._lock:
            if self.index_path.exists() and self.metadata_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                    with open(self.metadata_path, "r", encoding="utf-8") as f:
                        self.metadata_records = json.load(f)
                    logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors from {self.index_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to load FAISS index from disk: {e}. Initializing fresh index.")
                    self.index = faiss.IndexFlatIP(self.dimension)
                    self.metadata_records = []
                    return False
            else:
                logger.info("No existing FAISS index found. Initialized fresh empty index.")
                return True

vector_store = FAISSVectorStore()
