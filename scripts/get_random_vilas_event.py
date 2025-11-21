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

def get_random_event():
    logging.info("Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            df = pd.read_sql("SELECT * FROM property_events WHERE \"CountyName\" = 'VILAS' ORDER BY RANDOM() LIMIT 1;", connection)
        
        if not df.empty:
            event = df.iloc[0]
            logging.info("--- Random Vilas County Event ---")
            logging.info(f"  raw_parcel_identification: {event['raw_parcel_identification']}")
            logging.info(f"  PropertyAddress: {event['PropertyAddress']}")
        else:
            logging.info("No events found for Vilas County.")

    except Exception as e:
        logging.error(f"Failed to fetch random event: {e}")

if __name__ == "__main__":
    get_random_event()

