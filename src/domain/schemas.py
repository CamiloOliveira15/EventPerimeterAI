from pydantic import BaseModel
from datetime import datetime

class EventBase(BaseModel):
    camera_id: str
    event_type: str
    plate_number: str | None = None
    confidence: float | None = None
    snapshot_path: str | None = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
