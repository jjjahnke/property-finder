import os
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy as sa
import logging
import zipfile
import glob

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details from environment variables
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb') # Use the service name from docker-compose
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DATA_DIR = '/app/data'
TARGET_TABLE = 'properties'
TARGET_CRS = 'EPSG:4326' # WGS 84

# --- Main Ingestion Logic ---

def find_gdb_zip_path():
    """Finds the first file ending with 'GDB.zip' in the data directory."""
    search_pattern = os.path.join(DATA_DIR, '*GDB.zip')
    zip_files = glob.glob(search_pattern)
    if not zip_files:
        logging.error(f"No '*GDB.zip' file found in {DATA_DIR}")
        return None
    if len(zip_files) > 1:
        logging.warning(f"Multiple GDB.zip files found. Using the first one: {zip_files[0]}")
    return zip_files[0]

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

def ingest_geodata():
    """
    Reads geospatial data from a GDB.zip file, transforms it, and loads it
    into the 'properties' table in the PostGIS-enabled database.
    """
    logging.info("Starting geospatial data ingestion...")

    gdb_zip_path = find_gdb_zip_path()
    if not gdb_zip_path:
        return

    logging.info(f"Found GDB zip file: {gdb_zip_path}")

    try:
        gdb_uri = f"zip://{gdb_zip_path}"
        logging.info(f"Reading geodata from: {gdb_uri}")
        gdf = gpd.read_file(gdb_uri)
        logging.info(f"Successfully read {len(gdf)} features.")
        logging.info(f"Original CRS: {gdf.crs}")

    except Exception as e:
        logging.error(f"Failed to read geodatabase file: {e}")
        return

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
        null_ids_log_path = os.path.join(DATA_DIR, 'null_synthetic_ids_geodata.csv')
        logging.info(f"Logging details of null synthetic_stateids to {null_ids_log_path}")
        null_synthetic_ids[['PARCELID', 'PARCELFIPS']].to_csv(null_ids_log_path, index=False)

    # --- Handle Duplicates based on synthetic_stateid ---
    if 'synthetic_stateid' in gdf.columns:
        duplicates = gdf[gdf.duplicated(subset=['synthetic_stateid'], keep=False)]
        if not duplicates.empty:
            logging.warning(f"Found {len(duplicates)} duplicated rows based on 'synthetic_stateid'.")
            
            log_cols = ['synthetic_stateid', 'STATEID', 'PARCELID', 'TAXPARCELID', 'PARCELDATE', 'TAXROLLYEAR', 'OWNERNME1']
            cols_to_log = [col for col in log_cols if col in duplicates.columns]
            
            duplicates_log_path = os.path.join(DATA_DIR, 'duplicates_synthetic_stateid.csv')
            logging.info(f"Logging details of duplicates to {duplicates_log_path}")
            duplicates[cols_to_log].to_csv(duplicates_log_path, index=False)

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
        logging.info(f"Connecting to database at {DB_HOST}...")
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

    except Exception as e:
        logging.error(f"Failed to load data into the database: {e}")

if __name__ == "__main__":
    ingest_geodata()
