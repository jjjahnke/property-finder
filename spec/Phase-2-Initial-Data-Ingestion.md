# Spec: Phase 2 - Initial Data Ingestion

**Status:** `pending`

This document outlines the tasks required to build the initial data ingestion pipeline for both geospatial and event data.

## TODO List

- [x] Create a `data/` directory for local data files and add it to `.gitignore`.
- [x] Mount the `data/` directory into the `backend` service in `docker-compose.yml`.
- [x] Add necessary libraries (e.g., `geopandas`) to `requirements.txt`.
- [x] Create a geospatial ingestion script (`ingest_geodata.py`) to:
    - [x] Process the `GDB.zip` file.
    - [x] Connect to TimescaleDB.
    - [x] Load the data into the `properties` table.
- [x] Create an event producer script (`producer.py`) to:
    - [x] Process the `CSV.zip` file.
    - [x] Publish individual property events to RabbitMQ.
- [ ] Create an event consumer script (`consumer.py`) to:
    - [ ] Listen for events from RabbitMQ.
    - [ ] Insert event data into the `property_events` hypertable.
- [ ] Update the `Makefile` with targets to run the new ingestion scripts.
- [x] ~~Implement a direct-to-DB ingestion script for all event data.~~
- [x] ~~Handle missing `event_date` values by using `DateRecorded` as a fallback.~~
- [x] ~~Filter event data to only include records for Vilas County.~~
- [x] ~~Normalize `parcel_id` formats to ensure consistency between datasets.~~
- [x] ~~Construct and join on `STATEID` based on schema documentation.~~
- [x] Successfully load an initial batch of 35 event records into the database.
- [ ] Refine `parcel_id` normalization to capture more of the 16,662 orphan events.
- [ ] Investigate `data/duplicates.csv` to understand the cause of duplicate parcel IDs.
- [ ] Investigate `data/missing_event_dates.csv` to understand the cause of missing or invalid event dates.