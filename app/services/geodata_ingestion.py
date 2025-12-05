import os
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.orm import Session
import logging
from app.core.config import settings # Assuming DATABASE_URL will be in settings later or passed directly

# --- Configuration (can be overridden by environment variables in K8s) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost') # Default for local, K8s will override
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

TARGET_TABLE = 'properties'
TARGET_CRS = 'EPSG:4326' # WGS 84

# --- Helper Functions (from original ingest_geodata.py) ---

def create_synthetic_stateid(row):
    """
    Creates a synthetic STATEID from PARCELFIPS and PARCELID.
    - Normalizes PARCELID by removing non-alphanumeric characters.
    - Zero-pads PARCELFIPS to 3 digits.
    - Combines them to create a consistent, joinable key.
    """
    parcel_id = row.get('PARCELID')
    fips_code = row.get('PARCELFIPS')

    if pd.isna(parcel_id) or pd.isna(fips_code):
        return None

    # Normalize parcel_id: remove all non-alphanumeric characters
    normalized_parcel_id = ''.join(filter(str.isalnum, str(parcel_id))).upper()
    
    # Format FIPS code to be a zero-padded 3-digit string
    formatted_fips = str(int(fips_code)).zfill(3)
    
    return f"{formatted_fips}{normalized_parcel_id}"

# --- Core Ingestion Logic --- 

def ingest_geodata_from_path(gdb_path: str):
    """
    Reads geospatial data from a GDB directory, transforms it, and loads it
    into the 'properties' table in the PostGIS-enabled database.
    """
    logging.info(f"Starting geospatial data ingestion from: {gdb_path}")

    if not os.path.exists(gdb_path):
        logging.error(f"GDB directory not found: {gdb_path}")
        raise FileNotFoundError(f"GDB directory not found: {gdb_path}")

    try:
        logging.info(f"Reading geodata from: {gdb_path}")
        gdf = gpd.read_file(gdb_path)
        logging.info(f"Successfully read {len(gdf)} features.")
        logging.info(f"Original CRS: {gdf.crs}")

    except Exception as e:
        logging.error(f"Failed to read geodatabase directory {gdb_path}: {e}")
        raise RuntimeError(f"Failed to read geodatabase: {e}")

    # --- Data Transformation ---
    gdf.rename(columns={'geometry': 'geom'}, inplace=True)
    gdf = gdf.set_geometry('geom')

    # --- Data Type Conversion ---
    date_cols = ['PARCELDATE', 'LOADDATE']
    for col in date_cols:
        if col in gdf.columns:
            gdf[col] = pd.to_datetime(gdf[col], errors='coerce').dt.date

    numeric_cols = ['TAXROLLYEAR', 'CNTASSDVALUE', 'LNDVALUE', 'IMPVALUE', 'MFLVALUE', 
                    'ESTFMKVALUE', 'NETPRPTA', 'GRSPRPTA']
    for col in numeric_cols:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors='coerce')

    # --- Synthetic STATEID Creation ---
    logging.info("Creating synthetic_stateid...")
    gdf['synthetic_stateid'] = gdf.apply(create_synthetic_stateid, axis=1)
    logging.info("Finished creating synthetic_stateid.")
    
    # Log records where synthetic_stateid is null
    null_synthetic_ids = gdf[gdf['synthetic_stateid'].isnull()]
    if not null_synthetic_ids.empty:
        logging.warning(f"Found {len(null_synthetic_ids)} records with null synthetic_stateid.")
        # In an API context, we might not write to a shared DATA_DIR. Just log.
        # null_ids_log_path = os.path.join(DATA_DIR, 'null_synthetic_ids_geodata.csv')
        # logging.info(f"Logging details of null synthetic_stateids to {null_ids_log_path}")
        # null_synthetic_ids[['PARCELID', 'PARCELFIPS']].to_csv(null_ids_log_path, index=False)

    # --- Handle Duplicates based on synthetic_stateid ---
    if 'synthetic_stateid' in gdf.columns:
        duplicates = gdf[gdf.duplicated(subset=['synthetic_stateid'], keep=False)]
        if not duplicates.empty:
            logging.warning(f"Found {len(duplicates)} duplicated rows based on 'synthetic_stateid'.")
            # Log duplicates or handle as per policy
            initial_rows = len(gdf)
            gdf.drop_duplicates(subset=['synthetic_stateid'], keep='first', inplace=True)
            final_rows = len(gdf)
            logging.info(f"Removed {initial_rows - final_rows} duplicate records. {final_rows} unique records remain.")
        else:
            logging.info("No duplicate synthetic_stateids found.")

    # --- CRS Transformation ---
    if gdf.crs != TARGET_CRS:
        logging.info(f"Reprojecting data from {gdf.crs} to {TARGET_CRS}...")
        gdf = gdf.to_crs(TARGET_CRS)

    # --- Database Loading ---
    try:
        logging.info(f"Connecting to database...")
        engine = create_engine(DATABASE_URL)

        logging.info(f"Clearing all existing data from '{TARGET_TABLE}' table...")
        with engine.connect() as connection:
            connection.execute(sa.text(f'TRUNCATE TABLE "{TARGET_TABLE}" RESTART IDENTITY CASCADE;'))
            connection.commit()

        logging.info(f"Loading data into '{TARGET_TABLE}' table...")
        gdf.to_postgis(
            TARGET_TABLE,
            engine,
            if_exists='append',
            index=False,
            chunksize=1000
        )
        logging.info(f"Successfully loaded {len(gdf)} records into '{TARGET_TABLE}'.")
        return {"status": "success", "message": f"Ingested {len(gdf)} records.", "records_ingested": len(gdf)}

    except Exception as e:
        logging.error(f"Failed to load data into the database: {e}")
        raise RuntimeError(f"Database ingestion failed: {e}")
