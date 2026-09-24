import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base

class RecognitionEvent(Base):
    __tablename__ = "recognition_events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="UNKNOWN")  # KNOWN, UNKNOWN, LOW_QUALITY, VERIFYING
    similarity = Column(Float, nullable=False, default=0.0)
    quality = Column(Float, nullable=False, default=0.0)
    camera_id = Column(String(64), nullable=False, default="0")
    bbox = Column(String(64), nullable=True)  # x1,y1,x2,y2
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    person = relationship("Person", back_populates="events")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    source = Column(String(256), nullable=False)  # "0", "1", "rtsp://..."
    resolution = Column(String(32), default="1280x720")
    fps = Column(Integer, default=30)
    status = Column(String(32), default="DISCONNECTED")  # CONNECTED, DISCONNECTED, ERROR
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
