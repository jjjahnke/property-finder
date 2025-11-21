import os
import pandas as pd
import geopandas as gpd
import zipfile
import glob
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
DATA_DIR = '/app/data'

# --- Helper Functions ---

def print_header(title):
    """Prints a formatted header."""
    print("\n" + "="*80)
    print(f"--- {title}")
    print("="*80)

def find_zip_path(extension):
    """Finds the first file with a given extension in the data directory."""
    search_pattern = os.path.join(DATA_DIR, f"*{extension}")
    zip_files = glob.glob(search_pattern)
    if not zip_files:
        logging.error(f"No '*{extension}' file found in {DATA_DIR}")
        return None
    if len(zip_files) > 1:
        logging.warning(f"Multiple *{extension} files found. Using the first one: {zip_files[0]}")
    return zip_files[0]

def inspect_csv_zip(csv_zip_path):
    """Inspects the contents of the CSV zip file."""
    print_header(f"Inspecting CSV Zip File: {os.path.basename(csv_zip_path)}")
    try:
        with zipfile.ZipFile(csv_zip_path, 'r') as z:
            file_list = z.namelist()
            print(f"Files inside zip: {file_list}")

            csv_filename = next((f for f in file_list if f.lower().endswith('.csv')), None)
            if not csv_filename:
                logging.error("No CSV file found inside the zip archive.")
                return

            print(f"\n--- Analyzing CSV: {csv_filename} ---")
            with z.open(csv_filename) as f:
                # Read only the first 5 rows to inspect headers and types
                df = pd.read_csv(f, nrows=5, low_memory=False)
                print("First 5 rows:")
                print(df.to_markdown(index=False))
                print("\nColumn Names and Inferred Data Types:")
                print(df.info())

    except Exception as e:
        logging.error(f"Could not process CSV zip file: {e}")

def inspect_gdb_zip(gdb_zip_path):
    """Inspects the contents of the GDB zip file."""
    print_header(f"Inspecting GDB Zip File: {os.path.basename(gdb_zip_path)}")
    try:
        gdb_uri = f"zip://{gdb_zip_path}"
        print(f"Attempting to read from URI: {gdb_uri}")

        # List layers if possible (requires fiona)
        try:
            import fiona
            layers = fiona.listlayers(gdb_uri)
            print(f"Layers found in GDB: {layers}")
        except Exception as e:
            print(f"Could not list layers (this is often okay): {e}")


        # Read the first 5 features to inspect schema
        gdf = gpd.read_file(gdb_uri, rows=5)
        print("\nFirst 5 features:")
        # Print without geometry for readability
        print(pd.DataFrame(gdf.drop(columns='geometry')).to_markdown(index=False))
        print("\nColumn Names and Inferred Data Types:")
        print(gdf.info())
        print(f"\nCoordinate Reference System (CRS): {gdf.crs}")

    except Exception as e:
        logging.error(f"Could not process GDB zip file: {e}")
        logging.error("This can happen if the zip file doesn't contain a .gdb directory at the root, or if required drivers are missing.")


if __name__ == "__main__":
    csv_zip = find_zip_path('CSV.zip')
    if csv_zip:
        inspect_csv_zip(csv_zip)

    gdb_zip = find_zip_path('GDB.zip')
    if gdb_zip:
        inspect_gdb_zip(gdb_zip)
