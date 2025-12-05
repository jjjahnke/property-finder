import os
import time
import uuid
import sys
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
    """Initializes or recreates the Qdrant collection if it doesn't exist or for a clean rebuild."""
    collection_name = COLLECTION_NAME
    
    if client.collection_exists(collection_name=collection_name):
        print(f"Collection '{collection_name}' already exists. Deleting for a fresh start...")
        client.delete_collection(collection_name=collection_name)
        # Give Qdrant a moment to clean up
        time.sleep(2)
    
    print(f"Creating collection '{collection_name}' with vector size {vector_size}...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    print(f"Collection '{collection_name}' created.")


def get_sharded_parcel_data(engine):
    """Retrieves parcel IDs and text to embed based on hash-modulo sharding."""
    print(f"Retrieving parcels for shard {JOB_COMPLETION_INDEX}/{TOTAL_SHARDS}...")
    
    # Construct a comprehensive text representation for embedding
    # We use COALESCE to handle NULLs and separate fields with spaces
    query = text(f"""
        SELECT 
            "PARCELID",
            TRIM(
                COALESCE("OWNERNME1", '') || ' ' || 
                COALESCE("SITEADRESS", '') || ' ' || 
                COALESCE("PLACENAME", '') || ' ' || 
                COALESCE("ZIPCODE", '')
            ) as embedding_text
        FROM properties
        WHERE ABS(hashtext("PARCELID")) % :total_shards = :job_completion_index
    """)
    
    with engine.connect() as connection:
        result = connection.execute(query, {
            "total_shards": TOTAL_SHARDS,
            "job_completion_index": JOB_COMPLETION_INDEX
        }).fetchall()
    
    # Filter out rows where embedding_text might be empty or just whitespace
    data = [(row[0], row[1]) for row in result if row[1] and row[1].strip()]
    
    print(f"Found {len(data)} parcels for shard {JOB_COMPLETION_INDEX}.")
    return data

def main():
    print("Starting Qdrant Indexer...", flush=True)
    db_engine = get_db_engine()
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    model = SentenceTransformer(MODEL_NAME)
    
    # Get model's embedding size
    vector_size = model.get_sentence_embedding_dimension()
    initialize_qdrant_collection(qdrant_client, vector_size)

    parcel_data = get_sharded_parcel_data(db_engine)

    if not parcel_data:
        print("No parcel IDs to process for this shard. Exiting.", flush=True)
        return

    # Process in chunks to avoid OOM
    batch_size = 20000
    total_records = len(parcel_data)
    print(f"Processing {total_records} records in batches of {batch_size}...", flush=True)

    for i in range(0, total_records, batch_size):
        batch = parcel_data[i : i + batch_size]
        print(f"Processing batch {i // batch_size + 1}/{(total_records + batch_size - 1) // batch_size}...", flush=True)
        
        parcel_ids = [item[0] for item in batch]
        texts_to_embed = [item[1] for item in batch]

        # Generate embeddings
        embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()

        # Prepare points for Qdrant
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, parcel_id)), 
                vector=embedding,
                payload={"parcel_id": parcel_id, "text": text_content}
            )
            for parcel_id, text_content, embedding in zip(parcel_ids, texts_to_embed, embeddings)
        ]

        # Upload to Qdrant
        operation_info = qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points,
        )
        print(f"Batch {i // batch_size + 1} upsert status: {operation_info.status}", flush=True)

    print("Qdrant Indexer finished.", flush=True)
    
    # Cleanup
    db_engine.dispose()
    sys.exit(0)

if __name__ == "__main__":
    main()
