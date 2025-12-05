from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.property import Property as PydanticProperty
from app.db.models import Property as SQLAlchemyProperty
from qdrant_client import QdrantClient
import os

router = APIRouter()

@router.get("/vector-stats")
def get_vector_stats():
    """Returns statistics about the vector database (Qdrant)."""
    try:
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant-service")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        client = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        collection_name = "parcel_embeddings"
        count_result = client.count(collection_name=collection_name, exact=True)
        
        return {
            "collection": collection_name,
            "count": count_result.count,
            "status": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Qdrant: {e}")

@router.get("/{property_id}", response_model=PydanticProperty)
def read_property(property_id: int, db: Session = Depends(get_db)):
    db_property = (
        db.query(SQLAlchemyProperty).filter(SQLAlchemyProperty.id == property_id).first()
    )
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_property
