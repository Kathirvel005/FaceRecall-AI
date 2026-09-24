import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class FaceSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_path: str
    quality_score: float
    created_at: datetime.datetime

class PersonBase(BaseModel):
    student_id: str = Field(..., json_schema_extra={"example": "STU001"})
    name: str = Field(..., json_schema_extra={"example": "Kathirvel"})
    department: Optional[str] = Field(None, json_schema_extra={"example": "Computer Science"})
    class_name: Optional[str] = Field(None, json_schema_extra={"example": "CSE-A"})
    email: Optional[str] = Field(None, json_schema_extra={"example": "kathirvel@example.com"})
    profile_image: Optional[str] = None
    active: bool = True

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    class_name: Optional[str] = None
    email: Optional[str] = None
    profile_image: Optional[str] = None
    active: Optional[bool] = None

class PersonResponse(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    samples_count: int = 0
    samples: List[FaceSampleResponse] = []

class EnrollmentSample(BaseModel):
    image_base64: str
    quality_score: float = 1.0

class EnrollmentRequest(BaseModel):
    samples: List[EnrollmentSample]
