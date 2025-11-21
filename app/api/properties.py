from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.property import Property

router = APIRouter()

@router.get("/{property_id}", response_model=Property)
def read_property(property_id: int, db: Session = Depends(get_db)):
    # Placeholder for database logic
    db_property = {"id": property_id, "synthetic_stateid": "dummy-state-id"} # Replace with actual DB query
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_property
