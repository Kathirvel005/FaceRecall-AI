import os
from pathlib import Path
from typing import List, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    FACES_DIR: Path = DATA_DIR / "faces"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    LOGS_DIR: Path = DATA_DIR / "logs"
    MODELS_DIR: Path = BASE_DIR / "models"

    # Environment & Device
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DEVICE_PREFERENCE: str = "auto"  # 'auto', 'cuda', 'cpu'

    # Models
    DETECTION_MODEL_PATH: str = "models/det_10g.onnx"
    RECOGNITION_MODEL_PATH: str = "models/w600k_r50.onnx"
    DETECTION_INPUT_SIZE: str = "640,640"
    DETECTION_CONF_THRESHOLD: float = 0.35
    DETECTION_NMS_THRESHOLD: float = 0.40

    # Face Quality Parameters (Tuned for real-world webcam conditions)
    MIN_FACE_SIZE: int = 35
    BLUR_THRESHOLD: float = 10.0  # Laplacian variance (webcam friendly)
    MIN_BRIGHTNESS: float = 30.0
    MAX_BRIGHTNESS: float = 235.0
    MAX_YAW_DEG: float = 50.0
    MAX_PITCH_DEG: float = 40.0
    MIN_QUALITY_SCORE: float = 0.20

    # Recognition Parameters (Tuned for high live accuracy)
    SIMILARITY_THRESHOLD: float = 0.40
    UNKNOWN_THRESHOLD: float = 0.35
    TOP_K_CANDIDATES: int = 5
    EMBEDDING_DIM: int = 512

    # Tracking & Temporal Smoothing (Fast lock-on, zero flicker)
    TRACKER_MAX_AGE: int = 30
    TRACKER_MIN_HITS: int = 1
    TRACKER_IOU_THRESHOLD: float = 0.25
    TEMPORAL_VOTE_WINDOW: int = 4
    TEMPORAL_CONFIRM_THRESHOLD: float = 0.40
    DETECTION_INTERVAL: int = 1
    RECOGNITION_INTERVAL: int = 2

    # Camera Pipeline
    DEFAULT_CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 1280
    CAMERA_HEIGHT: int = 720
    CAMERA_FPS: int = 30

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/classroom_faces.db"
    FAISS_INDEX_PATH: str = "data/embeddings/faiss.index"
    METADATA_STORE_PATH: str = "data/embeddings/metadata.json"

    # Security
    SECRET_KEY: str = "super-secret-production-key-change-me-123456"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpassword"

    # Liveness
    LIVENESS_ENABLED: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    @property
    def detection_shape(self) -> Tuple[int, int]:
        parts = [int(p.strip()) for p in self.DETECTION_INPUT_SIZE.split(",")]
        return (parts[0], parts[1])


settings = Settings()
