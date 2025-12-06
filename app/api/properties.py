from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.property import Property as PydanticProperty
from app.db.models import Property as SQLAlchemyProperty
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os

router = APIRouter()

# Initialize Qdrant Client and Model once
# Using environment variables for configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant-service")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Lazy loading or global initialization? 
# Global is simpler for now, but startup might be slower.
print(f"Loading embedding model: {MODEL_NAME}...", flush=True)
embedding_model = SentenceTransformer(MODEL_NAME)
print("Model loaded.", flush=True)

@router.post("/match")
def match_properties(
    query: str = Body(..., embed=True, description="The messy address or text to match against."),
    limit: int = 5,
    threshold: float = 0.0
):
    """
    Finds the nearest property records for a given text query.
    """
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collection_name = "parcel_embeddings"
        
        # Generate embedding for the query text
        query_vector = embedding_model.encode(query).tolist()
        
        # Search Qdrant using query_points (search is deprecated/removed in v1.10+)
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=threshold if threshold > 0 else None
        ).points
        
        results = []
        for scored_point in search_result:
            results.append({
                "parcel_id": scored_point.payload.get("parcel_id"),
                "score": scored_point.score,
                "text": scored_point.payload.get("text"), # The text that was embedded
            })
            
        return {"query": query, "matches": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching failed: {e}")

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
