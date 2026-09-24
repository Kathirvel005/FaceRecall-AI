from typing import List, Optional
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort

from backend.app.config import settings
from backend.app.core.logging import logger

class ArcFaceRecognizer:
    """
    ArcFace / InsightFace 512-D Feature Embedding Generator using ONNX Runtime.
    Includes automatic L2 normalization for direct cosine distance and FAISS search.
    Supports replaceable models (ResNet50 / MobileFaceNet) and dynamic batching.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device_preference: Optional[str] = None
    ):
        self.model_path = model_path or settings.RECOGNITION_MODEL_PATH
        self.device_preference = device_preference or settings.DEVICE_PREFERENCE
        self.session: Optional[ort.InferenceSession] = None
        self.embedding_dim = settings.EMBEDDING_DIM
        self._init_session()

    def _init_session(self):
        resolved_path = Path(self.model_path)
        if not resolved_path.is_absolute():
            resolved_path = settings.BASE_DIR / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"ArcFace model not found at: {resolved_path}")

        available_providers = ort.get_available_providers()
        providers = []
        if self.device_preference in ("auto", "cuda") and "CUDAExecutionProvider" in available_providers:
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        logger.info(f"Loading ArcFace Recognizer from {resolved_path} with providers: {providers}")
        self.session = ort.InferenceSession(str(resolved_path), sess_options, providers=providers)

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        active_provider = self.session.get_providers()[0]
        logger.info(f"ArcFace Recognizer initialized successfully. Active Provider: {active_provider}")

    def _preprocess_single(self, aligned_bgr: np.ndarray) -> np.ndarray:
        """
        Normalize 112x112 BGR to ArcFace RGB input tensor (1, 3, 112, 112).
        """
        if aligned_bgr.shape[:2] != (112, 112):
            aligned_bgr = cv2.resize(aligned_bgr, (112, 112))

        # Convert BGR to RGB
        rgb_img = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB)
        # Normalization: (RGB - 127.5) / 127.5
        normalized = (rgb_img.astype(np.float32) - 127.5) / 127.5
        # HWC to CHW
        chw = normalized.transpose((2, 0, 1))
        return chw

    def extract_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Generate a normalized 512-D embedding vector for a single aligned face.
        """
        if aligned_face is None or aligned_face.size == 0 or self.session is None:
            return np.zeros(self.embedding_dim, dtype=np.float32)

        tensor = self._preprocess_single(aligned_face)
        batch_tensor = np.expand_dims(tensor, axis=0)

        raw_emb = self.session.run([self.output_name], {self.input_name: batch_tensor})[0]
        norm = np.linalg.norm(raw_emb, ord=2, axis=1, keepdims=True)
        normalized_emb = raw_emb / (norm + 1e-10)
        return normalized_emb.flatten().astype(np.float32)

    def extract_batch(self, aligned_faces: List[np.ndarray]) -> np.ndarray:
        """
        Batch extraction for multiple faces in a single inference call.
        """
        if not aligned_faces or self.session is None:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        tensors = [self._preprocess_single(f) for f in aligned_faces]
        batch_tensor = np.stack(tensors, axis=0)

        raw_embs = self.session.run([self.output_name], {self.input_name: batch_tensor})[0]
        norms = np.linalg.norm(raw_embs, ord=2, axis=1, keepdims=True)
        normalized_embs = raw_embs / (norms + 1e-10)
        return normalized_embs.astype(np.float32)

face_recognizer = ArcFaceRecognizer()
