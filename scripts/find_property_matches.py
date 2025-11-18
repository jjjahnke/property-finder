import pandas as pd
from sqlalchemy import create_engine
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def find_matches():
    logging.info("Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # --- Get all Vilas County Property Records ---
            property_df = pd.read_sql("SELECT \"PARCELID\" FROM properties WHERE \"CONAME\" = 'VILAS'", connection)
            
            # --- Build Hash Tables ---
            logging.info("Building hash tables from property PARCELIDs...")
            property_parcel_map_s1 = set()
            property_parcel_map_s2 = {}
            for index, row in property_df.iterrows():
                if pd.notna(row['PARCELID']):
                    # Strategy 1: No normalization on property PARCELID
                    property_parcel_map_s1.add(str(row['PARCELID']).strip().upper())
                    # Strategy 2: Universal normalization on property PARCELID
                    normalized_id = ''.join(filter(str.isalnum, str(row['PARCELID']))).upper()
                    property_parcel_map_s2[normalized_id] = row['PARCELID']
            logging.info(f"Lookup set for Strategy 1 built with {len(property_parcel_map_s1)} unique PARCELIDs.")
            logging.info(f"Hash table for Strategy 2 built with {len(property_parcel_map_s2)} unique normalized PARCELIDs.")

            # --- Get all Vilas County Event Records ---
            event_df = pd.read_sql("SELECT \"raw_parcel_identification\" FROM property_events WHERE \"CountyName\" = 'VILAS'", connection)
            logging.info(f"Found {len(event_df)} events for Vilas County.")

            # --- Perform Matching ---
            matches_s1 = 0
            matches_s2 = 0
            for index, row in event_df.iterrows():
                if (index + 1) % 1000 == 0:
                    logging.info(f"Processing event {index + 1}/{len(event_df)}...")
                if pd.notna(row['raw_parcel_identification']):
                    raw_event_id = str(row['raw_parcel_identification']).strip().upper()
                    
                    # Strategy 1: Strip PRCL only
                    cleaned_event_id_s1 = raw_event_id[4:] if raw_event_id.startswith('PRCL') else raw_event_id
                    if cleaned_event_id_s1 in property_parcel_map_s1:
                        matches_s1 += 1

                    # Strategy 2: Universal Normalization
                    cleaned_event_id_s2 = re.sub(r'^PRCL[0-9]{3}-', '', raw_event_id)
                    normalized_event_id_s2 = ''.join(filter(str.isalnum, cleaned_event_id_s2)).upper()
                    if normalized_event_id_s2 in property_parcel_map_s2:
                        matches_s2 += 1

            logging.info("\n--- Results ---")
            logging.info(f"Strategy 1 (Strip PRCL only): {matches_s1} matches")
            logging.info(f"Strategy 2 (Universal Normalization): {matches_s2} matches")

    except Exception as e:
        logging.error(f"Failed to find matches: {e}")
