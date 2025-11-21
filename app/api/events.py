from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.event import PropertyEvent
import datetime

router = APIRouter()

@router.get("/{event_id}", response_model=PropertyEvent)
def read_event(event_id: int, db: Session = Depends(get_db)):
    # Placeholder for database logic
    db_event = {"id": event_id, "property_id": 1, "event_type": "sale", "event_date": datetime.datetime.now()} # Replace with actual DB query
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event
