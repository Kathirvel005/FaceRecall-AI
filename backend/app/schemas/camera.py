import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CameraBase(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "cam-0"})
    name: str = Field(..., json_schema_extra={"example": "Classroom Front Camera"})
    source: str = Field(..., json_schema_extra={"example": "0"})  # "0", "1", or rtsp url
    resolution: str = Field(default="1280x720")
    fps: int = Field(default=30)
    is_active: bool = True

class CameraCreate(CameraBase):
    pass

class CameraResponse(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    status: str
    created_at: datetime.datetime

class CameraStatus(BaseModel):
    id: str
    name: str
    source: str
    is_running: bool
    current_fps: float
    resolution: str
    dropped_frames: int
