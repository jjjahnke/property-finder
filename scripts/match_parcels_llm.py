import pandas as pd
from sqlalchemy import create_engine, text
import os
import logging
import requests
import json

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Ollama configuration
OLLAMA_API_URL = "http://192.168.150.59:11434/api/generate"
OLLAMA_MODEL = "llama3"

# Data paths
DATA_DIR = '/app/data'
ORPHAN_EVENTS_FILE = os.path.join(DATA_DIR, 'orphan_events.csv')

def get_data_for_matching():
    """
    Fetches detailed data for orphan events and valid properties.
    """
    try:
        logging.info(f"Reading orphan events from {ORPHAN_EVENTS_FILE}...")
        orphan_df = pd.read_csv(ORPHAN_EVENTS_FILE, usecols=['parcel_id', 'PropertyAddress', 'GranteeZip']).drop_duplicates(subset=['parcel_id'])
        orphan_df = orphan_df.dropna(subset=['PropertyAddress', 'GranteeZip'])
        orphan_records = orphan_df.to_dict('records')
        logging.info(f"Found {len(orphan_records)} unique orphan records with address and zip.")

        logging.info("Connecting to the database to fetch valid property data...")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Fetch records where SITEADRESS and ZIPCODE are not null
            query = text('SELECT "STATEID", "SITEADRESS", "ZIPCODE" FROM properties WHERE "SITEADRESS" IS NOT NULL AND "ZIPCODE" IS NOT NULL;')
            result = connection.execute(query)
            valid_properties_df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        # Convert ZIPCODE to string for consistent matching
        valid_properties_df['ZIPCODE'] = valid_properties_df['ZIPCODE'].astype(str).str.strip()
        logging.info(f"Found {len(valid_properties_df)} valid properties with address and zip.")
        
        return orphan_records, valid_properties_df

    except Exception as e:
        logging.error(f"Failed to get data for matching: {e}")
        return None, None

def construct_prompt(orphan_record, candidate_properties):
    """Constructs the detailed prompt for the LLM."""
    
    prompt = f"""
Objective: You are an expert in data cleaning and entity resolution. Your task is to find the best match for an "Orphan Property" from a list of "Candidate Properties".

Matching Criteria:
1.  **Address Similarity:** The `SITEADRESS` of the candidate should be very similar to the `PropertyAddress` of the orphan. Consider variations like "ST" vs "STREET", "RD" vs "ROAD", and minor typos.
2.  **Parcel ID Similarity:** The `STATEID` of the candidate should contain numeric parts that are similar to the orphan's `parcel_id`.

Task:
- Analyze the "Orphan Property" provided below.
- Compare it against the "Candidate Properties".
- If you find one clear, highly confident match based on both address and parcel ID similarity, return ONLY its `STATEID`.
- If there is no single best match or you are not confident, return the exact string "NO_MATCH".

---
**Orphan Property:**
{json.dumps(orphan_record, indent=2)}

**Candidate Properties (filtered by zip code):**
{json.dumps(candidate_properties, indent=2)}

---
**Your Answer (either the single best STATEID or NO_MATCH):**
"""
    return prompt

def match_parcels_with_llm(orphans, properties_df, num_to_process=10):
    """
    Sends individual orphan records to the LLM for matching against candidates.
    """
    logging.info(f"Starting advanced parcel matching with model '{OLLAMA_MODEL}'...")
    
    # Process a small sample of the orphans
    orphans_to_process = orphans[:num_to_process]
    
    for orphan in orphans_to_process:
        try:
            # Find candidates by zip code
            orphan_zip = str(orphan.get('GranteeZip', '')).split('.')[0]
            if not orphan_zip:
                continue

            candidates = properties_df[properties_df['ZIPCODE'] == orphan_zip].to_dict('records')
            
            if not candidates:
                logging.warning(f"No candidates found for orphan {orphan['parcel_id']} with zip {orphan_zip}")
                continue

            prompt = construct_prompt(orphan, candidates)
            
            logging.info(f"Sending orphan {orphan['parcel_id']} to the Ollama server for matching...")
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
            response.raise_for_status()
            
            result = response.json()
            llm_output = result.get("response", "").strip()
            
            print(f"Orphan: {orphan['parcel_id']} -> Match: {llm_output}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to communicate with Ollama server for orphan {orphan.get('parcel_id')}: {e}")
            break # Stop on API error
        except Exception as e:
            logging.error(f"An error occurred while processing orphan {orphan.get('parcel_id')}: {e}")

if __name__ == "__main__":
    orphan_records, valid_properties_df = get_data_for_matching()
    if orphan_records and not valid_properties_df.empty:
        match_parcels_with_llm(orphan_records, valid_properties_df)
    else:
        logging.error("Could not retrieve data for matching. Aborting.")
