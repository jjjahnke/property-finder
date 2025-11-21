import pandas as pd
from sqlalchemy import create_engine
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def analyze_formats():
    logging.info("Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            df = pd.read_sql_table('properties', connection)
        logging.info(f"Successfully loaded {len(df)} records from the 'properties' table.")
    except Exception as e:
        logging.error(f"Failed to load data from database: {e}")
        return

    if 'CONAME' not in df.columns or 'PARCELID' not in df.columns:
        logging.error("The 'properties' table must contain 'CONAME' and 'PARCELID' columns.")
        return

    # Group by county and analyze PARCELID formats
    county_groups = df.groupby('CONAME')

    logging.info("\n--- PARCELID Format Analysis by County ---")
    for county_name, group in county_groups:
        print(f"\nCounty: {county_name}")
        # Get up to 5 unique parcel IDs for sampling
        sample_parcel_ids = group['PARCELID'].unique()[:5]
        for pid in sample_parcel_ids:
            print(f"  - {pid}")

if __name__ == "__main__":
    analyze_formats()
