# Project Context and State Summary

## Overall Goal
The primary objective is to ingest real estate transfer return (RETR) event data (from statewide CSVs) and link it to geospatial property data (from a Vilas County GDB file) in a TimescaleDB database.

## Current Strategy: Synthetic State ID
Our investigation has revealed that a direct join on existing keys (`PARCELID`, `TAXPARCELID`, `STATEID`) is unreliable due to inconsistencies. The agreed-upon strategy is to **create a new, synthetic, and consistently formatted key** in both datasets and use that for joining.

This `synthetic_stateid` will be constructed by:
1.  Aggressively normalizing the local parcel ID from both sources (stripping all non-alphanumeric characters, removing leading zeros).
2.  Concatenating the zero-padded, 3-digit county FIPS code with the normalized parcel ID.

## Key Findings & Discoveries
1.  **`TAXPARCELID` is Unusable:** The `TAXPARCELID` column in the geospatial GDB data is entirely `NULL` for Vilas County. It cannot be used as a join key.
2.  **`PARCELID` is Inconsistent:** The `PARCELID` in the GDB data is not a reliable unique identifier. It contains non-ID text values like "HYDRO", "ROW", and "GAP OR OVERLAP".
3.  **`STATEID` is Flawed for Joining:** While the `STATEID` in the `properties` table is correctly constructed (`PARCELFIPS` + `PARCELID`), it cannot be reliably matched by the event data because the underlying `PARCELID` formats are fundamentally different and inconsistent between the two sources.
4.  **Data Scope Mismatch:** The property data is for **Vilas County only**, while the event data is **statewide**. This requires filtering the event data for `CountyName == 'VILAS'`.
5.  **Event Date Issues:** The primary date field for events, `DeedDate`, is often `NULL`. We must use `DateRecorded` as a fallback to get a valid timestamp for events.

## State of Key Files
*   **`ingest_events.py`:** This script is in a good state. It successfully implements a multi-stage matching process (normalization and partial ID matching) that has ingested up to **4,637 records**. It is ready to be modified to use the new `synthetic_stateid` strategy.
*   **`ingest_geodata.py`:** This script is in its original, functional state. It **needs to be modified** to create the `synthetic_stateid` column for the property data. My previous attempts to do this have failed and should be disregarded.
*   **`alembic/versions/...`:** The database schema currently uses `STATEID` for the foreign key relationship. This will need to be updated to use `synthetic_stateid`.
*   **`spec/Phase-2-Matching-Logic.md`:** This file exists and documents the intended strategy.

## Immediate Next Step for New Agent
The very next action should be to implement the **Synthetic State ID** strategy. This involves:
1.  Correctly modifying `ingest_geodata.py` to add a `synthetic_stateid` column to the properties data.
2.  Modifying `ingest_events.py` to create and use the exact same `synthetic_stateid`.
3.  Updating the Alembic migration to create the database schema with the new `synthetic_stateid` key.
