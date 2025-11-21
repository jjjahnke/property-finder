from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PropertyEvent(BaseModel):
    id: int
    property_id: int
    event_type: str
    event_date: datetime
    details: Optional[dict] = None

    class Config:
        from_attributes = True
