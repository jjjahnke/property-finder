import os
import pandas as pd
import zipfile
import glob
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATA_DIR = '/app/data'

def discover_event_columns():
    """
    Reads all CSV.zip files, compares their headers, and prints the columns if they are consistent.
    """
    search_pattern = os.path.join(DATA_DIR, '*CSV.zip')
    zip_files = glob.glob(search_pattern) + glob.glob(os.path.join(DATA_DIR, '*csv.zip')) # Case-insensitive glob

    if not zip_files:
        logging.error(f"No '*CSV.zip' or '*csv.zip' files found in {DATA_DIR}")
        return

    logging.info(f"Found {len(zip_files)} CSV zip files to inspect.")

    master_columns = None
    is_consistent = True

    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                csv_filename = next((f for f in z.namelist() if f.lower().endswith('.csv')), None)
                if not csv_filename:
                    logging.warning(f"No CSV file found inside {zip_path}. Skipping.")
                    continue

                with z.open(csv_filename) as f:
                    # Read only the header by reading the first row
                    df_header = pd.read_csv(f, nrows=0, encoding='latin-1')
                    current_columns = df_header.columns.tolist()
                    logging.info(f"Columns in {zip_path}/{csv_filename}: {len(current_columns)} columns.")

                    if master_columns is None:
                        master_columns = current_columns
                        logging.info("Established master column list from the first file.")
                    elif master_columns != current_columns:
                        logging.error(f"Schema inconsistency found in {zip_path}/{csv_filename}!")
                        is_consistent = False
                        # Find and report differences for easier debugging
                        master_set = set(master_columns)
                        current_set = set(current_columns)
                        if master_set - current_set:
                            logging.error(f"  - Missing columns: {sorted(list(master_set - current_set))}")
                        if current_set - master_set:
                            logging.error(f"  - Extra columns: {sorted(list(current_set - master_set))}")
                        
        except Exception as e:
            logging.error(f"Failed to process file {zip_path}: {e}")
            is_consistent = False

    if master_columns:
        print("\n--- Master Column List ---")
        for column in master_columns:
            print(column)
        print("--- End of Columns ---")

    if not is_consistent:
        logging.error("\n--- Schema is INCONSISTENT across files. Please review the errors above. ---")


if __name__ == "__main__":
    discover_event_columns()