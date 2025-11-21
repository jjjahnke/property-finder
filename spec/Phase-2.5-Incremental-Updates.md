# Phase 2.5 - Incremental Updates and Change Tracking Specification

This document outlines the architectural changes required to support incremental monthly data updates, including handling additions, modifications, and deletions of properties and events. This approach replaces the previous "truncate and reload" strategy with a more robust system for tracking changes over time.

## 1. Core Objective

The primary goal is to modify the data ingestion process to:

-   Preserve the history of properties and property events across monthly data imports.
-   Identify and track new properties, updated properties, and properties that are no longer present in the data feed.
-   Ensure that the `property_events` table is appended with new data, rather than being overwritten.

## 2. Database Schema Changes

To support these requirements, the following changes will be made to the database schema.

### 2.1. `properties` Table

A new column will be added to the `properties` table to enable "soft deletes." This allows us to retain records for historical purposes even if they are no longer in the latest data import.

-   **`is_active` (boolean):** This column will be `true` if the property is present in the most recent data import and `false` otherwise.

A new Alembic migration will be created to apply this change to the database.

## 3. Ingestion Script Modifications

The existing ingestion scripts will be updated as follows:

### 3.1. `ingest_geodata.py` (Property Data)

The property ingestion script will be rewritten to perform the following steps:

1.  **Mark All Existing Properties as Inactive:** Before processing the new data file, the script will execute an `UPDATE` statement to set `is_active = false` for all records in the `properties` table.
2.  **Process New Data with "Upsert" Logic:** For each property in the new data file, the script will:
    a.  Generate the `synthetic_stateid`.
    b.  Attempt to find an existing record in the `properties` table with the same `synthetic_stateid`.
    c.  **If a record exists (Update):** The script will update the existing record with the new information from the data file and set `is_active = true`.
    d.  **If no record exists (Insert):** The script will insert a new record into the `properties` table with the new property's data and set `is_active = true`.
3.  **Log Changes:** The script will be updated to log additions and updates as events in the `property_events` table, providing a clear history of changes.

### 3.2. `ingest_events.py` (Property Event Data)

The property event ingestion script will be modified to perform incremental updates:

1.  **Identify New Events:** The script will determine which events in the new data file are not already present in the `property_events` table. This will require a stable unique identifier for each event.
2.  **Insert Only New Events:** The script will only insert the new events, leaving existing records untouched.

## 4. API Service Considerations

The API service will be designed with these changes in mind:

-   The `GET /properties/` endpoint will, by default, only return properties where `is_active = true`.
-   A new query parameter (e.g., `include_inactive=true`) will be added to allow clients to retrieve all properties, including inactive ones.

This updated approach ensures that the property-finder application maintains a complete and accurate history of all property data over time.
