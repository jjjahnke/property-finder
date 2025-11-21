import os
import geopandas as gpd
import zipfile
import glob
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATA_DIR = '/app/data'

def find_gdb_zip_path():
    """Finds the first file ending with 'GDB.zip' in the data directory."""
    search_pattern = os.path.join(DATA_DIR, '*GDB.zip')
    zip_files = glob.glob(search_pattern)
    if not zip_files:
        logging.error(f"No '*GDB.zip' file found in {DATA_DIR}")
        return None
    return zip_files[0]

def discover_columns():
    """Reads the GDB file and prints all column names."""
    gdb_zip_path = find_gdb_zip_path()
    if not gdb_zip_path:
        return

    try:
        gdb_uri = f"zip://{gdb_zip_path}"
        logging.info(f"Reading schema from: {gdb_uri}")
        gdf = gpd.read_file(gdb_uri, rows=1) # Read only one row to get the schema quickly
        
        print("--- Discovered GDB Columns ---")
        for column in gdf.columns:
            print(column)
        print("--- End of Columns ---")

    except Exception as e:
        logging.error(f"Failed to read geodatabase file: {e}")

if __name__ == "__main__":
    discover_columns()
