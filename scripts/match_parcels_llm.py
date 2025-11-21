import pandas as pd
from sqlalchemy import create_engine, text
import os
import logging
from fuzzywuzzy import fuzz

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Data paths
DATA_DIR = '/app/data'
ORPHAN_EVENTS_FILE = os.path.join(DATA_DIR, 'orphan_events.csv')

# Fuzzy matching thresholds
ADDRESS_SIMILARITY_THRESHOLD = 80 # Adjust as needed
PARCEL_ID_SIMILARITY_THRESHOLD = 80 # Adjust as needed

def normalize_string(s):
    """Normalizes a string for comparison (uppercase, remove punctuation, extra spaces)."""
    if not isinstance(s, str):
        return ""
    s = s.upper().strip()
    s = ' '.join(s.split()) # Replace multiple spaces with single space
    # Remove common punctuation that might differ but not change meaning
    s = s.replace('.', '').replace(',', '').replace('-', '').replace('/', '')
    return s

def get_data_for_matching():
    """
    Fetches detailed data for orphan events and valid properties.
    """
    try:
        logging.info(f"Reading orphan events from {ORPHAN_EVENTS_FILE}...")
        orphan_df = pd.read_csv(ORPHAN_EVENTS_FILE, usecols=['parcel_id', 'PropertyAddress', 'GranteeZip']).drop_duplicates(subset=['parcel_id'])
        orphan_df = orphan_df.dropna(subset=['parcel_id', 'PropertyAddress', 'GranteeZip'])
        orphan_records = orphan_df.to_dict('records')
        logging.info(f"Found {len(orphan_records)} unique orphan records with address and zip.")

        logging.info("Connecting to the database to fetch valid property data...")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            query = text('SELECT "STATEID", "PARCELID", "SITEADRESS", "ZIPCODE" FROM properties WHERE "SITEADRESS" IS NOT NULL AND "ZIPCODE" IS NOT NULL AND "PARCELID" IS NOT NULL;')
            result = connection.execute(query)
            valid_properties_df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        valid_properties_df['ZIPCODE'] = valid_properties_df['ZIPCODE'].astype(str).str.strip()
        valid_properties_df['normalized_siteaddress'] = valid_properties_df['SITEADRESS'].apply(normalize_string)
        valid_properties_df['normalized_parcelid'] = valid_properties_df['PARCELID'].apply(normalize_string)

        logging.info(f"Found {len(valid_properties_df)} valid properties with address and zip.")
        
        return orphan_records, valid_properties_df

    except Exception as e:
        logging.error(f"Failed to get data for matching: {e}")
        return None, None

def find_best_match(orphan_record, candidate_properties_df):
    """
    Finds the best matching STATEID for an orphan record among candidates
    using fuzzy matching on address and parcel ID.
    """
    best_match_stateid = "NO_MATCH"
    highest_combined_score = 0

    normalized_orphan_address = normalize_string(orphan_record['PropertyAddress'])
    normalized_orphan_parcel_id = normalize_string(orphan_record['parcel_id'])

    for _, candidate in candidate_properties_df.iterrows():
        address_score = fuzz.ratio(normalized_orphan_address, candidate['normalized_siteaddress'])
        parcel_id_score = fuzz.ratio(normalized_orphan_parcel_id, candidate['normalized_parcelid'])
        
        # Combine scores - you might want to weight these differently
        combined_score = (address_score + parcel_id_score) / 2

        if combined_score > highest_combined_score and \
           address_score >= ADDRESS_SIMILARITY_THRESHOLD and \
           parcel_id_score >= PARCEL_ID_SIMILARITY_THRESHOLD:
            highest_combined_score = combined_score
            best_match_stateid = candidate['STATEID']
            
    return best_match_stateid

def match_parcels_programmatically(orphans, properties_df, num_to_process=100):
    """
    Processes orphan records programmatically to find matches.
    """
    logging.info("Starting programmatic fuzzy parcel matching...")
    
    orphans_to_process = orphans[:num_to_process]
    match_count = 0

    logging.info("--- Proposed Mappings (from programmatic logic) ---")
    for orphan in orphans_to_process:
        orphan_zip = str(orphan.get('GranteeZip', '')).split('.')[0]
        if not orphan_zip:
            print(f"Orphan: {orphan['parcel_id']} -> Match: NO_MATCH (Missing Zip)")
            continue

        # Filter candidates by zip code (blocking step)
        candidate_properties_df = properties_df[properties_df['ZIPCODE'] == orphan_zip]
        
        if candidate_properties_df.empty:
            print(f"Orphan: {orphan['parcel_id']} -> Match: NO_MATCH (No candidates for zip {orphan_zip})")
            continue

        best_match = find_best_match(orphan, candidate_properties_df)
        
        if best_match != "NO_MATCH":
            match_count += 1
        print(f"Orphan: {orphan['parcel_id']} -> Match: {best_match}")

    logging.info(f"Found {match_count} potential matches out of {len(orphans_to_process)} orphans processed.")
    logging.info("--- End of Mappings ---")

if __name__ == "__main__":
    orphan_records, valid_properties_df = get_data_for_matching()
    if orphan_records and not valid_properties_df.empty:
        match_parcels_programmatically(orphan_records, valid_properties_df)
    else:
        logging.error("Could not retrieve data for matching. Aborting.")
