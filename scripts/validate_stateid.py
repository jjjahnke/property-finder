import pandas as pd
from sqlalchemy import create_engine, text
import os
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def validate_stateid_construction(sample_size=20):
    """
    Validates that the STATEID in the properties table is correctly constructed
    from PARCELFIPS and PARCELID.
    """
    logging.info("Starting STATEID validation...")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            query = text(f'SELECT "STATEID", "PARCELFIPS", "PARCELID" FROM properties WHERE "PARCELFIPS" IS NOT NULL AND "PARCELID" IS NOT NULL LIMIT {sample_size};')
            result = connection.execute(query)
            properties_sample_df = pd.DataFrame(result.fetchall(), columns=result.keys())

        if properties_sample_df.empty:
            logging.warning("No properties with both PARCELFIPS and PARCELID found to validate.")
            return

        logging.info(f"--- Validating {len(properties_sample_df)} Records ---")
        validation_errors = 0
        
        for _, row in properties_sample_df.iterrows():
            existing_stateid = row['STATEID']
            parcelfips = row['PARCELFIPS']
            parcelid = row['PARCELID']
            
            # Ensure parcelfips is a zero-padded 3-digit string
            formatted_fips = str(parcelfips).zfill(3)
            
            constructed_stateid = formatted_fips + str(parcelid)
            
            if existing_stateid == constructed_stateid:
                logging.info(f"OK: {existing_stateid} == {constructed_stateid}")
            else:
                logging.error(f"FAIL: Existing='{existing_stateid}', Constructed='{constructed_stateid}'")
                validation_errors += 1
        
        logging.info("--- End of Validation ---")
        if validation_errors == 0:
            logging.info("STATEID validation successful for the sample. The format appears correct.")
        else:
            logging.warning(f"{validation_errors} validation errors found. The STATEID format may be inconsistent.")

    except Exception as e:
        logging.error(f"An error occurred during STATEID validation: {e}")

if __name__ == "__main__":
    validate_stateid_construction()
