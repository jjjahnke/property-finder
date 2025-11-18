import os
import pandas as pd
from sqlalchemy import create_engine, text
import sqlalchemy as sa
import logging
import zipfile
import glob

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details from environment variables
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DATA_DIR = '/app/data'
TARGET_TABLE = 'property_events'

from ingest_geodata import ingest_geodata

# --- Main Ingestion Logic ---

def find_csv_zip_paths():
    """Finds all files ending with 'CSV.zip' or 'csv.zip' in the data directory."""
    search_pattern_upper = os.path.join(DATA_DIR, '*CSV.zip')
    search_pattern_lower = os.path.join(DATA_DIR, '*csv.zip')
    zip_files = glob.glob(search_pattern_upper) + glob.glob(search_pattern_lower)
    return zip_files

def ingest_events():
    """
    Reads event data from all CSV.zip files, transforms it, and loads it
    into the 'property_events' table in the database.
    """
    logging.info("Starting raw event data ingestion...")

    csv_zip_paths = find_csv_zip_paths()
    if not csv_zip_paths:
        logging.error(f"No '*CSV.zip' or '*csv.zip' files found in {DATA_DIR}")
        return

    logging.info(f"Found {len(csv_zip_paths)} CSV zip files for ingestion.")

    all_dfs = []
    for zip_path in csv_zip_paths:
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                csv_filename = next((f for f in z.namelist() if f.lower().endswith('.csv')), None)
                if not csv_filename:
                    logging.warning(f"No CSV file found inside {zip_path}. Skipping.")
                    continue
            
                logging.info(f"Reading CSV file: {zip_path}/{csv_filename}")
                with z.open(csv_filename) as f:
                    df = pd.read_csv(f, low_memory=False, encoding='latin-1')
                    all_dfs.append(df)

        except Exception as e:
            logging.error(f"Failed to read or process CSV file {zip_path}: {e}")
            continue

    if not all_dfs:
        logging.error("No dataframes were successfully read. Exiting.")
        return

    # Concatenate all dataframes
    full_df = pd.concat(all_dfs, ignore_index=True)
    logging.info(f"Successfully read {len(full_df)} total rows from all CSVs.")

    # --- Data Transformation ---
    full_df.rename(columns={'ParcelIdentification': 'raw_parcel_identification', 'DeedDate': 'event_date'}, inplace=True)

    # Drop the 'Unnamed: 89' column if it exists
    if 'Unnamed: 89' in full_df.columns:
        full_df.drop(columns=['Unnamed: 89'], inplace=True)
        logging.info("Dropped 'Unnamed: 89' column.")

    # Convert date columns
    date_cols = ['DateRecorded', 'DateConveyed', 'event_date', 'CertificationDate', 'GranteeCertificationDate']
    for col in date_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_datetime(full_df[col], errors='coerce')

    # Convert numeric columns
    numeric_cols = [
        'YearCaptured', 'MultiFamilyUnits', 'TotalAcres', 'LotSize1', 'LotSize',
        'ManagedForestLandAcres', 'WaterFrontFeet', 'PersPropertyValueExcluded',
        'PersPropertyValueExempt', 'TotalRealEstateValue', 'TransferFee'
    ]
    for col in numeric_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce')

    # --- Handle Missing Event Dates ---
    full_df['event_date'] = pd.to_datetime(full_df['event_date'], errors='coerce')
    full_df['DateRecorded'] = pd.to_datetime(full_df['DateRecorded'], errors='coerce')
    full_df['event_date'].fillna(full_df['DateRecorded'], inplace=True)
    full_df.dropna(subset=['event_date'], inplace=True)

    # Add event_type and source columns
    full_df['event_type'] = 'sale'
    full_df['source'] = 'RETR_CSV'

    # Generate a simple event_id for each unique event
    full_df['event_id'] = range(1, len(full_df) + 1)

    # --- Database Loading ---
    try:
        logging.info(f"Connecting to database at {DB_HOST}...")
        engine = create_engine(DATABASE_URL)

        logging.info(f"Clearing all existing data from '{TARGET_TABLE}' table...")
        with engine.connect() as connection:
            connection.execute(sa.text(f'TRUNCATE TABLE "{TARGET_TABLE}" RESTART IDENTITY CASCADE;'))
            connection.commit()

        logging.info(f"Loading data into '{TARGET_TABLE}' table...")
        full_df.to_sql(
            TARGET_TABLE,
            engine,
            if_exists='append',
            index=False,
            chunksize=1000,
            dtype={'event_date': sa.DateTime(timezone=True)}
        )
        logging.info(f"Successfully loaded {len(full_df)} records into '{TARGET_TABLE}'.")

    except Exception as e:
        logging.error(f"Failed to load data into the database: {e}")

if __name__ == "__main__":
    ingest_events()
