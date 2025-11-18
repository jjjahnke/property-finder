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

def ingest_events():
    """
    Reads event data from all CSV.zip files, transforms it, and loads it
    into the 'property_events' table in the database.
    """
    # First, ensure the geospatial data is ingested and the properties table is populated
    logging.info("Running geospatial data ingestion first to ensure properties table is populated...")
    ingest_geodata()
    logging.info("Geospatial data ingestion complete.")

    logging.info("Starting event data ingestion...")

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
    logging.info(f"Original columns: {full_df.columns.tolist()}")

    # --- Data Transformation ---
    # Rename ParcelIdentification to PARCELID and DeedDate to event_date
    full_df.rename(columns={'ParcelIdentification': 'PARCELID', 'DeedDate': 'event_date'}, inplace=True)

    # Normalize the PARCELID to match the format in the properties table
    if 'PARCELID' in full_df.columns:
        logging.info("Normalizing PARCELID format by stripping PRCL prefix...")
        # Strips 'PRCL' and the county code prefix (e.g., 'PRCL002-')
        full_df['PARCELID'] = full_df['PARCELID'].str.replace(r'^PRCL[0-9]{3}-', '', regex=True)
        logging.info("PARCELID normalization complete.")

    # Drop the 'Unnamed: 89' column if it exists
    if 'Unnamed: 89' in full_df.columns:
        full_df.drop(columns=['Unnamed: 89'], inplace=True)
        logging.info("Dropped 'Unnamed: 89' column.")

    # --- Synthetic STATEID Creation ---
    county_fips_map = {
        'ADAMS': '001', 'ASHLAND': '003', 'BARRON': '005', 'BAYFIELD': '007', 'BROWN': '009',
        'BUFFALO': '011', 'BURNETT': '013', 'CALUMET': '015', 'CHIPPEWA': '017', 'CLARK': '019',
        'COLUMBIA': '021', 'CRAWFORD': '023', 'DANE': '025', 'DODGE': '027', 'DOOR': '029',
        'DOUGLAS': '031', 'DUNN': '033', 'EAU CLAIRE': '035', 'FLORENCE': '037', 'FOND DU LAC': '039',
        'FOREST': '041', 'GRANT': '043', 'GREEN': '045', 'GREEN LAKE': '047', 'IOWA': '049',
        'IRON': '051', 'JACKSON': '053', 'JEFFERSON': '055', 'JUNEAU': '057', 'KENOSHA': '059',
        'KEWAUNEE': '061', 'LA CROSSE': '063', 'LAFAYETTE': '065', 'LANGLADE': '067', 'LINCOLN': '069',
        'MANITOWOC': '071', 'MARATHON': '073', 'MARINETTE': '075', 'MARQUETTE': '077', 'MENOMINEE': '078',
        'MILWAUKEE': '079', 'MONROE': '081', 'OCONTO': '083', 'ONEIDA': '085', 'OUTAGAMIE': '087',
        'OZAUKEE': '089', 'PEPIN': '091', 'PIERCE': '093', 'POLK': '095', 'PORTAGE': '097',
        'PRICE': '099', 'RACINE': '101', 'RICHLAND': '103', 'ROCK': '105', 'RUSK': '107',
        'ST CROIX': '109', 'SAUK': '111', 'SAWYER': '113', 'SHAWANO': '115', 'SHEBOYGAN': '117',
        'TAYLOR': '119', 'TREMPEALEAU': '121', 'VERNON': '123', 'VILAS': '125', 'WALWORTH': '127',
        'WASHBURN': '129', 'WASHINGTON': '131', 'WAUKESHA': '133', 'WAUPACA': '135', 'WAUSHARA': '137',
        'WINNEBAGO': '139', 'WOOD': '141'
    }
    if 'CountyName' in full_df.columns:
        logging.info("Constructing synthetic_stateid for event data...")
        full_df['PARCELFIPS'] = full_df['CountyName'].str.upper().map(county_fips_map)
        full_df['synthetic_stateid'] = full_df.apply(create_synthetic_stateid, axis=1)
        logging.info("synthetic_stateid construction complete.")
        

        
    else:
        logging.error("CountyName column not found, cannot construct synthetic_stateid.")
        return

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

    # --- Filter by County ---
    if 'CountyName' in full_df.columns:
        initial_rows = len(full_df)
        full_df = full_df[full_df['CountyName'] == 'VILAS']
        final_rows = len(full_df)
        logging.info(f"Filtered by CountyName='VILAS'. Kept {final_rows} records out of {initial_rows}.")
    else:
        logging.warning("CountyName column not found, cannot filter by county.")

    # --- Handle Missing Event Dates ---
    # Use DeedDate as the primary source, and DateRecorded as a fallback.
    full_df['event_date'] = pd.to_datetime(full_df['event_date'], errors='coerce')
    full_df['DateRecorded'] = pd.to_datetime(full_df['DateRecorded'], errors='coerce')
    
    # Use DateRecorded where event_date (from DeedDate) is null
    full_df['event_date'].fillna(full_df['DateRecorded'], inplace=True)

    # Now, identify and log rows where event_date is still null
    missing_dates_df = full_df[full_df['event_date'].isnull()]
    if not missing_dates_df.empty:
        logging.warning(f"Found {len(missing_dates_df)} rows where both DeedDate and DateRecorded are invalid.")
        
        log_cols = ['PARCELID', 'event_date', 'DateRecorded', 'SaleNumber', 'DocumentNumber', 'GrantorLastName', 'GranteeLastName']
        cols_to_log = [col for col in log_cols if col in missing_dates_df.columns]
        
        missing_dates_log_path = os.path.join(DATA_DIR, 'missing_event_dates.csv')
        logging.info(f"Logging details of these records to {missing_dates_log_path}")
        missing_dates_df[cols_to_log].to_csv(missing_dates_log_path, index=False)

        # Drop rows where a valid event_date could not be determined
        full_df.dropna(subset=['event_date'], inplace=True)
        logging.info(f"Removed {len(missing_dates_df)} records. {len(full_df)} records remain.")
    else:
        logging.info("All records have a valid event_date from either DeedDate or DateRecorded.")

    # Ensure required columns exist
    required_cols = ['synthetic_stateid', 'event_date']
    if not all(col in full_df.columns for col in required_cols):
        logging.error(f"Missing one or more critical columns after mapping: {required_cols}")
        logging.error(f"Available columns: {full_df.columns.tolist()}")
        return

    # Add event_type and source columns
    full_df['event_type'] = 'sale' # Default event type
    full_df['source'] = 'RETR_CSV' # Default source

    # --- Handle Duplicates (if any, based on primary key) ---
    # The primary key is (event_id, event_date). Since event_id is not in source, we need to generate it.
    # For now, we'll assume unique (synthetic_stateid, event_date) pairs are unique events.
    # If multiple events for the same parcel on the same date exist, we'll keep the first.
    initial_rows = len(full_df)
    full_df.sort_values(by=['synthetic_stateid', 'event_date'], inplace=True)
    full_df.drop_duplicates(subset=['synthetic_stateid', 'event_date'], keep='first', inplace=True)
    final_rows = len(full_df)
    if initial_rows > final_rows:
        logging.warning(f"Removed {initial_rows - final_rows} duplicate (synthetic_stateid, event_date) records.")
    else:
        logging.info("No duplicate (synthetic_stateid, event_date) records found.")

    # Generate a simple event_id for each unique event
    full_df['event_id'] = range(1, len(full_df) + 1)

    # --- Database Loading ---
    try:
        logging.info(f"Connecting to database at {DB_HOST}...")
        engine = create_engine(DATABASE_URL)

        # --- Multi-Stage Foreign Key Validation ---
        with engine.connect() as connection:
            logging.info("Fetching valid synthetic_stateids and PARCELIDs from 'properties' table for validation...")
            result = connection.execute(text("SELECT DISTINCT \"synthetic_stateid\", \"PARCELID\" FROM properties;"))
            properties_data = {row[0]: row[1] for row in result if row[0]}
            valid_synthetic_ids = set(properties_data.keys())
            logging.info(f"Found {len(valid_synthetic_ids)} unique synthetic_stateids in the properties table.")

        # Stage 1: Direct match
        matched_df = full_df[full_df['synthetic_stateid'].isin(valid_synthetic_ids)]
        orphan_df = full_df[~full_df['synthetic_stateid'].isin(valid_synthetic_ids)]
        logging.info(f"Stage 1 Direct Match: Found {len(matched_df)} matches.")
        logging.info(f"{len(orphan_df)} orphan events remain for Stage 2.")

        # Stage 2: Partial Parcel ID Matching
        if not orphan_df.empty:
            logging.info("Starting Stage 2: Partial Parcel ID Matching...")
            # Create a map from parts of valid PARCELIDs to their full synthetic_stateid
            partial_id_map = {}
            for synthetic_id, parcel_id in properties_data.items():
                if not parcel_id or not isinstance(parcel_id, str):
                    continue
                parts = parcel_id.split('-')
                for part in parts:
                    if part.isdigit():
                         partial_id_map[part] = synthetic_id
            
            def find_match_by_partial_id(row):
                raw_parcel_id = row.get('PARCELID')
                if not raw_parcel_id or not isinstance(raw_parcel_id, str):
                    return None
                
                # Use the raw, un-normalized PARCELID from the event data
                parts = raw_parcel_id.split('-')
                for part in parts:
                    if part.isdigit() and part in partial_id_map:
                        return partial_id_map[part]
                return None

            orphan_df['synthetic_stateid'] = orphan_df.apply(find_match_by_partial_id, axis=1)
            newly_matched_df = orphan_df.dropna(subset=['synthetic_stateid'])
            
            if not newly_matched_df.empty:
                matched_df = pd.concat([matched_df, newly_matched_df])
                logging.info(f"Stage 2 Partial Match: Found {len(newly_matched_df)} new matches.")
            
            final_orphan_count = len(orphan_df) - len(newly_matched_df)
            if final_orphan_count > 0:
                logging.warning(f"{final_orphan_count} orphan events remain after all matching stages.")
                orphan_log_path = os.path.join(DATA_DIR, 'orphan_events.csv')
                logging.info(f"Logging final orphan events to {orphan_log_path}")
                orphan_df[orphan_df['synthetic_stateid'].isnull()].to_csv(orphan_log_path, index=False)

        # Final set of events to be loaded
        full_df = matched_df
        logging.info(f"Total matched events to be loaded: {len(full_df)}")

        # Drop the intermediate columns
        full_df.drop(columns=['PARCELID', 'PARCELFIPS'], inplace=True)

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
            dtype={'event_date': sa.DateTime(timezone=True)} # Explicitly set types for critical columns
        )
        logging.info(f"Successfully loaded {len(full_df)} records into '{TARGET_TABLE}'.")

    except Exception as e:
        logging.error(f"Failed to load data into the database: {e}")

if __name__ == "__main__":
    ingest_events()
