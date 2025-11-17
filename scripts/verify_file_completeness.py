import os
import glob
import logging
from datetime import date, timedelta

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATA_DIR = '/app/data'

def verify_file_completeness():
    """
    Checks for missing monthly CSV files over the last 5 years, handling case-insensitive zip extensions.
    """
    # --- 1. Generate Expected File Prefixes ---
    end_date = date.today()
    start_date = date(end_date.year - 5, end_date.month, 1)
    
    expected_prefixes = set()
    current_date = start_date
    while current_date <= end_date:
        expected_prefixes.add(current_date.strftime('%Y%m'))
        # Move to the next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

    logging.info(f"Expecting {len(expected_prefixes)} monthly files from {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}.")

    # --- 2. Get Actual File Prefixes ---
    # Use a case-insensitive glob for zip extensions
    search_pattern_upper = os.path.join(DATA_DIR, '*CSV.zip')
    search_pattern_lower = os.path.join(DATA_DIR, '*csv.zip')
    zip_files = glob.glob(search_pattern_upper) + glob.glob(search_pattern_lower)
    
    actual_prefixes = set()
    for zip_path in zip_files:
        basename = os.path.basename(zip_path)
        # Extract the YYYYMM part from the filename, handling both CSV.zip and csv.zip
        if basename.lower().endswith('csv.zip') and len(basename) >= 10:
            prefix = basename[:6]
            if prefix.isdigit():
                actual_prefixes.add(prefix)

    # --- 3. Compare and Report ---
    missing_prefixes = sorted(list(expected_prefixes - actual_prefixes))

    if not missing_prefixes:
        print("\n--- File set is COMPLETE for the last 5 years. ---")
    else:
        print(f"\n--- Found {len(missing_prefixes)} MISSING monthly files: ---")
        for prefix in missing_prefixes:
            year = prefix[:4]
            month = prefix[4:]
            print(f"  - {year}-{month} (Expected file: {prefix}CSV.zip or {prefix}csv.zip)")

if __name__ == "__main__":
    verify_file_completeness()
