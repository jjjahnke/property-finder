# Phase 2 - Event Matching Logic Specification

This document outlines the multi-stage strategy for matching real estate transfer return (RETR) event records to the corresponding geospatial property records.

## 1. Initial Data Preparation

- **Load Geospatial Data:** Ingest all records from the Vilas County GDB file into the `properties` table.
- **Load Event Data:** Ingest all records from the statewide RETR CSV files.
- **Filter Events by County:** Filter the event data to only include records where `CountyName` is 'VILAS'.

## 2. Parcel ID Normalization

- **Strip Prefix:** Remove the `PRCL...-` prefix from the `parcel_id` in the event data.
- **Remove Leading Zeros:** Remove leading zeros from all numeric segments of the `parcel_id` (e.g., `010-0123` becomes `10-123`).
- **Add Missing Prefix:** For any `parcel_id` that does not contain a hyphen, prepend the `10-` prefix.

## 3. STATEID Construction

- **Create `STATEID`:** For each event record, construct a `STATEID` by concatenating the Vilas County FIPS code (`125`) with the normalized `parcel_id`.

## 4. Matching Stage 1: Direct `STATEID` Match

- **Initial Match:** Attempt to join the event data to the `properties` table using a direct match on the `STATEID` column.
- **Log Orphans:** Any event records that do not find a match are considered orphans and are passed to the next stage.

## 5. Matching Stage 2: Partial `parcel_id` Matching

- **Create Mapping:** Create a dictionary that maps each individual numeric part of a valid `PARCELID` (from the `properties` table) to the full `PARCELID`.
- **Apply Mapping:** For each remaining orphan event, use this map to find a corrected `parcel_id`.
- **Re-construct `STATEID`:** If a corrected `parcel_id` is found, re-construct the `STATEID` and attempt to match again.
- **Log Remaining Orphans:** Any event records that still do not find a match are passed to the next stage.

## 6. Matching Stage 3: Fuzzy Address Matching

- **Candidate Selection:** For each remaining orphan, create a list of candidate properties by finding all properties in the `properties` table that share the same zip code.
- **Fuzzy Comparison:** Use a fuzzy matching algorithm (e.g., `fuzzywuzzy`) to compare the normalized `PropertyAddress` of the orphan with the normalized `SITEADRESS` of the candidates.
- **Final Match:** If a high-confidence match is found based on both address similarity and some degree of `parcel_id` similarity, the event is considered matched.
- **Log Final Orphans:** Any events that still do not have a match are logged to `orphan_events.csv` for manual review.
