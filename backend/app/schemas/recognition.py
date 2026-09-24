import datetime
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field, ConfigDict

class QualityMetrics(BaseModel):
    face_size: int
    sharpness: float
    brightness: float
    yaw: float
    pitch: float
    detection_conf: float
    is_valid: bool
    quality_score: float
    reason: Optional[str] = None

class FaceDetectionResult(BaseModel):
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float
    landmarks: List[List[float]]  # 5 landmarks [[x, y], ...]

class FaceRecognitionResult(BaseModel):
    track_id: int
    person_id: Optional[str] = None
    name: str = "UNKNOWN"
    status: str = "UNKNOWN"  # KNOWN, UNKNOWN, LOW_QUALITY, VERIFYING
    similarity: float = 0.0
    quality: float = 0.0
    bbox: List[int]
    landmarks: Optional[List[List[float]]] = None
    liveness_score: Optional[float] = 1.0
    is_live: bool = True
    department: Optional[str] = None
    class_name: Optional[str] = None
    timestamp: str

class RecognitionFrameSummary(BaseModel):
    frame_id: int
    timestamp: str
    camera_id: str
    fps: float
    face_count: int
    known_count: int
    unknown_count: int
    inference_latency_ms: float
    frame_width: int = 1280
    frame_height: int = 720
    faces: List[FaceRecognitionResult]

class RecognitionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: Optional[int] = None
    student_id: Optional[str] = None
    name: Optional[str] = None
    track_id: int
    status: str
    similarity: float
    quality: float
    camera_id: str
    bbox: Optional[str] = None
    timestamp: datetime.datetime
