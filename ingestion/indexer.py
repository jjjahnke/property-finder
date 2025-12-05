import os
import time
from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# Environment variables
# Defaults are for local development (e.g. via port-forwarding).
# In Kubernetes, these are overridden by the Job manifest to use service names (e.g., 'postgres-service').
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "property_finder")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
TOTAL_SHARDS = int(os.getenv("TOTAL_SHARDS", "4"))
JOB_COMPLETION_INDEX = int(os.getenv("JOB_COMPLETION_INDEX", "0"))

COLLECTION_NAME = "parcel_embeddings"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def get_db_engine():
    """Establishes and returns a SQLAlchemy database engine."""
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)

def initialize_qdrant_collection(client: QdrantClient, vector_size: int):
    """Initializes the Qdrant collection if it doesn't exist."""
    try:
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        print(f"Collection '{COLLECTION_NAME}' recreated with vector size {vector_size}.")
    except Exception as e:
        print(f"Error recreating collection: {e}. Attempting to get if it exists.")
        # If recreate fails, try to get it, assuming it might already exist
        try:
            client.get_collection(collection_name=COLLECTION_NAME)
            print(f"Collection '{COLLECTION_NAME}' already exists.")
        except Exception as e_get:
            print(f"Failed to get collection either: {e_get}")
            raise

def get_sharded_parcel_ids(engine):
    """Retrieves parcel IDs based on hash-modulo sharding."""
    print(f"Retrieving parcels for shard {JOB_COMPLETION_INDEX}/{TOTAL_SHARDS}...")
    # In a real scenario, you'd select the text to embed, not just the ID.
    # For now, we'll just get the parcel_id as a placeholder.
    query = text(f"""
        SELECT parcel_id
        FROM properties
        WHERE ABS(hashtext(parcel_id)) % :total_shards = :job_completion_index
    """)
    with engine.connect() as connection:
        result = connection.execute(query, {
            "total_shards": TOTAL_SHARDS,
            "job_completion_index": JOB_COMPLETION_INDEX
        }).fetchall()
    parcel_ids = [row[0] for row in result]
    print(f"Found {len(parcel_ids)} parcels for shard {JOB_COMPLETION_INDEX}.")
    return parcel_ids

def main():
    print("Starting Qdrant Indexer...")
    db_engine = get_db_engine()
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    model = SentenceTransformer(MODEL_NAME)
    
    # Get model's embedding size
    vector_size = model.get_sentence_embedding_dimension()
    initialize_qdrant_collection(qdrant_client, vector_size)

    parcel_ids = get_sharded_parcel_ids(db_engine)

    if not parcel_ids:
        print("No parcel IDs to process for this shard. Exiting.")
        return

    # Generate embeddings
    print(f"Generating embeddings for {len(parcel_ids)} parcels...")
    embeddings = model.encode(parcel_ids, show_progress_bar=True).tolist()

    # Prepare points for Qdrant
    points = [
        models.PointStruct(
            id=idx, # Qdrant expects integer or UUID for ID. Using index for now.
            vector=embedding,
            payload={"parcel_id": parcel_id}
        )
        for idx, (parcel_id, embedding) in enumerate(zip(parcel_ids, embeddings))
    ]

    # Upload to Qdrant
    print(f"Uploading {len(points)} vectors to Qdrant collection '{COLLECTION_NAME}'...")
    operation_info = qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        wait=True,
        points=points,
    )
    print(f"Upsert operation status: {operation_info.status}")
    print("Qdrant Indexer finished.")

if __name__ == "__main__":
    main()
