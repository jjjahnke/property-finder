import pandas as pd
import zipfile
import os
import glob
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = '/app/data'

def find_csv_zip_paths():
    search_pattern_upper = os.path.join(DATA_DIR, '*CSV.zip')
    search_pattern_lower = os.path.join(DATA_DIR, '*csv.zip')
    zip_files = glob.glob(search_pattern_upper) + glob.glob(search_pattern_lower)
    return zip_files

def analyze_parcel_ids():
    logging.info("Starting granular ParcelIdentification analysis for all event files...")
    csv_zip_paths = find_csv_zip_paths()
    if not csv_zip_paths:
        logging.error("No CSV zip files found in data directory.")
        return

    total_starts_with_prcl = 0
    total_purely_numeric = 0
    total_hyphenated_numeric_non_prcl = 0
    total_empty_null = 0
    total_unclassified = 0
    total_processed_records = 0

    for zip_path in csv_zip_paths:
        logging.info(f"Analyzing ParcelIdentification in: {zip_path}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                csv_filename = next((f for f in z.namelist() if f.lower().endswith('.csv')), None)
                if not csv_filename:
                    logging.error(f"No CSV file found inside {zip_path}.")
                    continue
                
                with z.open(csv_filename) as f:
                    df = pd.read_csv(f, low_memory=False, encoding='latin-1')
                    
                    if 'ParcelIdentification' in df.columns:
                        parcel_ids = df['ParcelIdentification'].astype(str)
                        
                        for pid in parcel_ids:
                            total_processed_records += 1
                            pid_stripped = str(pid).strip()

                            if pd.isna(pid) or pid_stripped == '':
                                total_empty_null += 1
                            elif pid_stripped.startswith('PRCL'):
                                total_starts_with_prcl += 1
                            elif re.fullmatch(r'\\d+', pid_stripped):
                                total_purely_numeric += 1
                            elif re.fullmatch(r'\\d+(?:-\\d+)*', pid_stripped):
                                total_hyphenated_numeric_non_prcl += 1
                            else:
                                total_unclassified += 1
                    else:
                        logging.error(f"ParcelIdentification column not found in {csv_filename}.")
        except Exception as e:
            logging.error(f"Failed to read or process CSV file {zip_path}: {e}")

    logging.info("--- Overall Granular Analysis Summary ---")
    logging.info(f"  Total records processed: {total_processed_records}")
    logging.info(f"  Starts with 'PRCL': {total_starts_with_prcl}")
    logging.info(f"  Purely Numeric (non-PRCL): {total_purely_numeric}")
    logging.info(f"  Hyphenated Numeric (non-PRCL): {total_hyphenated_numeric_non_prcl}")
    logging.info(f"  Empty/Null: {total_empty_null}")
    logging.info(f"  Unclassified: {total_unclassified}")

if __name__ == "__main__":
    analyze_parcel_ids()