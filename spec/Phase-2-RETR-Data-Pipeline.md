# Spec: Phase 2 - Proof of Concept - First Data Pipeline (RETR Sales Data)

**Status:** `pending`

This document outlines the tasks required to build the first data pipeline proof of concept.

## TODO List

- [ ] Create the **Data Collector** service for bulk downloads.
- [ ] Implement the first collector module to download the WI Dept. of Revenue (RETR) sales data `.zip` file.
- [ ] Create the **Transformation Service**.
- [ ] Implement logic to:
    - [ ] Unzip the downloaded file.
    - [ ] Parse the sales data CSV.
    - [ ] Transform rows into `property_events` (event_type: 'sale').
    - [ ] Publish events to RabbitMQ.
- [ ] Implement a **Loading Service** (or logic within the Transformation service) to consume events from RabbitMQ and insert them into TimescaleDB.
- [ ] Set up the **Orchestrator (Prefect)** to manage the RETR pipeline.
- [ ] Create a Prefect flow that chains the collection, transformation, and loading steps.
