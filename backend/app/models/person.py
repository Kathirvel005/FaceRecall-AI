import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base

class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), index=True, nullable=False)
    department = Column(String(128), nullable=True)
    class_name = Column(String(64), nullable=True)
    email = Column(String(128), nullable=True)
    profile_image = Column(String(256), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    samples = relationship("FaceSample", back_populates="person", cascade="all, delete-orphan")
    events = relationship("RecognitionEvent", back_populates="person", cascade="all, delete-orphan")

class FaceSample(Base):
    __tablename__ = "face_samples"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    image_path = Column(String(256), nullable=False)
    embedding_reference = Column(String(128), nullable=True)
    quality_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    person = relationship("Person", back_populates="samples")
