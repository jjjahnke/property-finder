# Phase 4 - API Service and Ingestion Pipeline Specification

This document outlines the architecture for the property-finder API service and the modular, strategy-based ingestion pipeline.

## 1. Project Structure

The project will be organized into the following directory structure:

```
/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── properties.py
│   │   └── events.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   ├── property.py
│   │   └── event.py
│   └── core/
│       └── config.py
├── ingestion/
│   ├── main.py
│   ├── pipeline.py
│   └── stages/
│       ├── cleaning.py
│       ├── normalization/
│       │   ├── __init__.py
│       │   ├── county_map.py
│       │   ├── normalize.py
│       │   └── strategies/
│       │       ├── strip_prcl.py
│       │       ├── strip_prcl_fips.py
│       │       ├── universal_alphanumeric.py
│       │       └── default.py
│       ├── matching.py
│       └── loading.py
├── scripts/
│   ├── analyze_parcel_id_formats_by_county.py
│   └── ...
├── spec/
│   └── Phase-4-API-Service.md
├── tests/
│   └── ...
├── docker-compose.yml
├── Dockerfile.backend
└── ...
```

## 2. API Service (`app/`)

The API service will be a FastAPI application responsible for serving data from the `properties` and `property_events` tables.

### 2.1. API Endpoints (`app/api/`)

The following RESTful endpoints will be implemented:

*   `GET /properties/{property_id}`: Retrieve a single property by its ID.
*   `GET /properties/`: Retrieve a list of properties, with support for pagination and filtering (e.g., by county).
*   `GET /events/{event_id}`: Retrieve a single event by its ID.
*   `GET /events/`: Retrieve a list of events, with support for pagination and filtering (e.g., by county, date range).
*   `GET /properties/{property_id}/events`: Retrieve all events associated with a specific property.

### 2.2. Database Interaction (`app/db/`)

*   Database connections will be managed through a session manager in `app/db/session.py`.
*   SQLAlchemy will be used for database interaction.

### 2.3. Data Models (`app/models/`)

*   Pydantic models will be used to define the data structures for API requests and responses, ensuring data validation and clear schema documentation.

## 3. Ingestion Pipeline (`ingestion/`)

The ingestion process will be a modular, strategy-based pipeline, orchestrated by `ingestion/pipeline.py`.

### 3.1. Pipeline Stages (`ingestion/stages/`)

The pipeline will consist of the following stages:

1.  **Initial Cleaning:** Renaming columns, handling missing dates, etc.
2.  **PARCELID Normalization:** Applying county-specific normalization strategies.
3.  **`synthetic_stateid` Generation:** Creating the join key.
4.  **Direct Matching:** Joining on `synthetic_stateid` and separating orphans.
5.  **Fuzzy Address Matching:** Processing orphans to find more matches.
6.  **Final Load:** Combining matched data and loading to the database.

### 3.2. PARCELID Normalization (`ingestion/stages/normalization/`)

The normalization stage will use a pluggable, strategy-based system:

*   **`strategies/` directory:** Each file in this directory will represent a distinct normalization strategy (e.g., `strip_prcl.py`, `universal_alphanumeric.py`).
*   **`county_map.py`:** This file will contain a dictionary that maps each `CountyName` to a specific strategy module.
*   **`normalize.py`:** This file will contain the main `normalize_parcel_ids` function that reads the `county_map.py`, groups the data by county, and applies the appropriate strategy to each group.

This architecture ensures that the ingestion process is modular, scalable, and easy to maintain.
