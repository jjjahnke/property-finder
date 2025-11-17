# Spec: Phase 2 - Initial Data Ingestion

**Status:** `pending`

This document outlines the tasks required to build the initial data ingestion pipeline for both geospatial and event data.

## TODO List

- [ ] Create a `data/` directory for local data files and add it to `.gitignore`.
- [ ] Mount the `data/` directory into the `backend` service in `docker-compose.yml`.
- [ ] Add necessary libraries (e.g., `geopandas`) to `requirements.txt`.
- [ ] Create a geospatial ingestion script (`ingest_geodata.py`) to:
    - [ ] Process the `GDB.zip` file.
    - [ ] Connect to TimescaleDB.
    - [ ] Load the data into the `properties` table.
- [ ] Create an event producer script (`producer.py`) to:
    - [ ] Process the `CSV.zip` file.
    - [ ] Publish individual property events to RabbitMQ.
- [ ] Create an event consumer script (`consumer.py`) to:
    - [ ] Listen for events from RabbitMQ.
    - [ ] Insert event data into the `property_events` hypertable.
- [ ] Update the `Makefile` with targets to run the new ingestion scripts.