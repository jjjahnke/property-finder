from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.property import Property as PydanticProperty
from app.db.models import Property as SQLAlchemyProperty

router = APIRouter()


@router.get("/{property_id}", response_model=PydanticProperty)
def read_property(property_id: int, db: Session = Depends(get_db)):
    db_property = (
        db.query(SQLAlchemyProperty).filter(SQLAlchemyProperty.id == property_id).first()
    )
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_property
