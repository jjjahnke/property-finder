from fastapi import FastAPI, UploadFile, File, HTTPException
from app.api import properties, events
from app.core.config import settings
from app.services.geodata_ingestion import ingest_geodata_from_path
import os
import shutil
import tempfile
import zipfile

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(properties.router, prefix=f"{settings.API_V1_STR}/properties", tags=["properties"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["events"])

@app.post(f"{settings.API_V1_STR}/ingest-geodata")
async def ingest_geodata_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed for geospatial data ingestion.")

    temp_dir = None
    try:
        # Create a temporary directory to extract the GDB
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, file.filename)

        # Save the uploaded zip file
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find the GDB directory within the unzipped content
        # Assuming the zip contains a single GDB directory like V11.0.0_Wisconsin_Parcels_2025_10.3_Uncompressed.gdb
        gdb_unzipped_path = None
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path) and item.endswith(".gdb"):
                gdb_unzipped_path = item_path
                break
        
        if not gdb_unzipped_path:
            raise HTTPException(status_code=400, detail="No .gdb directory found within the uploaded zip file.")

        # Ingest data from the unzipped GDB path
        ingestion_result = ingest_geodata_from_path(gdb_unzipped_path)

        return {"message": "Geospatial data ingestion initiated successfully", "details": ingestion_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.get("/")
def read_root():
    return {"Hello": "World"}
