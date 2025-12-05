# Phase 2.6 - Ingestion Orchestration and Change Data Capture Specification

This document outlines the refined, two-pronged strategy for data ingestion. The core objective is to handle data from two distinct sources—authoritative state snapshots (GeoDB) and transactional event files (e.g., RETR)—to build a complete and auditable history of all property changes over time.

## 1. Core Architectural Principles

-   **`properties` Table as the Single Source of Truth for *Current* Data:** The `properties` table in the database will always reflect the most recent, complete state of a property as defined by the latest ingested GeoDB snapshot. This ensures fast and simple queries for the current state of any given property.

-   **`property_events` Table as the Historical Ledger:** The `property_events` hypertable will serve as a complete, chronological, and immutable audit log. It will capture every detected change, from any source, including property creations, updates, deactivations, and transactional events like sales.

## 2. Ingestion Orchestration

The ingestion pipeline will be orchestrated as a multi-step process that intelligently handles data from different sources.

### 2.1. Process 1: GeoDB Snapshot Reconciliation

This process runs when a new, complete GeoDB file is available. It is responsible for updating the "current state" and logging any detected changes.

1.  **Iterate Through New Snapshot:** The pipeline will process each property record in the new GeoDB file.
2.  **Compare and Identify Changes:** For each record, it will use the `synthetic_stateid` to find the corresponding record in the `properties` table.
    -   **If the property is new:** An `INSERT` is performed on the `properties` table, and a `PROPERTY_CREATED` event is logged in `property_events`.
    -   **If the property exists:** The pipeline will perform a field-by-field comparison between the new record and the existing database record.
        -   For **every field that has changed** (e.g., `OWNERNME1`, `CNTASSDVALUE`), the pipeline will:
            1.  `UPDATE` the field in the `properties` table to its new value.
            2.  `INSERT` a `PROPERTY_UPDATED` event into the `property_events` table. The `details` JSON field of this event will contain a structured log of the change, such as: `{"field": "OWNERNME1", "old_value": "Old Name", "new_value": "New Name"}`. The `source` for this event will be `'STATE_GEODB_SNAPSHOT'`.
3.  **Handle Deactivations:** After processing the entire file, the pipeline will identify any properties in the `properties` table that were not present in the new snapshot. These properties will be marked as inactive (`is_active = false`), and a `PROPERTY_DEACTIVATED` event will be logged in `property_events`.

### 2.2. Process 2: Transactional Event Ingestion

This process runs whenever new event-based files (e.g., RETR sales data) are available.

1.  **Normalize and Link:** For each event record, the pipeline's first task is to normalize the raw parcel identifier to generate the standard `synthetic_stateid`.
2.  **Link to Property:** It uses this `synthetic_stateid` to link the event to a parent property in the `properties` table.
3.  **Insert Event:** The pipeline then `INSERT`s the new event directly into the `property_events` table.
    -   The `event_type` will be specific to the transaction (e.g., `'SALE'`).
    -   The `source` will identify the origin of the file (e.g., `'RETR_CSV'`).

## 3. Example Data Flow

This two-pronged approach ensures a robust and complete data history. For example:

1.  A property sale occurs on **Jan 15th**.
2.  The RETR file is ingested on **Jan 20th**. A `'SALE'` event appears in `property_events`. The `properties` table is **not** updated and still shows the old owner.
3.  A new GeoDB snapshot is released on **March 1st**.
4.  The snapshot is ingested on **March 5th**. The pipeline detects the owner change. It **updates** the `properties` table to the new owner and inserts a `PROPERTY_UPDATED` event into `property_events`.

The final historical record in `property_events` for the property will correctly show the `'SALE'` event followed by the official ownership change, with sources and timestamps for both, providing a complete and auditable timeline.
