from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from src.core.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    event_type = Column(String, index=True) # lpr, face, perimeter
    
    # LPR specific
    plate_number = Column(String, index=True, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    snapshot_path = Column(String, nullable=True) # Path in MinIO/S3
