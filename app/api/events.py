from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.event import PropertyEvent as PydanticPropertyEvent
from app.db.models import PropertyEvent as SQLAlchemyPropertyEvent

router = APIRouter()


@router.get("/{event_id}", response_model=PydanticPropertyEvent)
def read_event(event_id: int, db: Session = Depends(get_db)):
    db_event = (
        db.query(SQLAlchemyPropertyEvent)
        .filter(SQLAlchemyPropertyEvent.event_id == event_id)
        .first()
    )
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event
