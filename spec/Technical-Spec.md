# TECHNICAL SPECIFICATION
### WI-RE Analysis Platform - v1.1

---

### 1. High-Level Architecture

The system will be a set of containerized microservices orchestrated by Kubernetes. Communication will be handled via synchronous REST APIs for user-facing requests and an asynchronous message queue for data processing pipelines.

**Architectural Diagram:**

```mermaid
graph TD
    subgraph User Interaction
        A[End User via Browser] --> B{API Gateway / Ingress};
    end

    subgraph Core Services
        B --> C[Web Service / UI<br>(Next.js)];
        B --> D[Orchestrator API<br>(Prefect)];
        B --> E[Backend API Service<br>(FastAPI)];
    end

    subgraph Data Plane
        F[TimescaleDB<br>(PostgreSQL)]
        G[Message Queue<br>(RabbitMQ)]
        H[Vector Database<br>(Qdrant)]
    end

    subgraph Data Pipeline
        I[ETL Transformation Service]
        J[Data Collectors / Workers]
        K[Entity Resolution Indexer<br>(GPU Job)]
    end

    C -- REST API --> E;
    D -- Triggers Jobs --> G;
    E -- SQL Queries --> F;
    E -- Vector Search --> H;
    E -- File Upload (Geodata) --> F;

    G -- Pub/Sub --> I;
    G -- Pub/Sub --> J;

    I -- Inserts Events --> F;
    J -- Publishes Raw Data --> G;
    
    K -- Embeddings --> H;
    K -- Reads Properties --> F;

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style H fill:#bbf,stroke:#333,stroke-width:2px
```

### 2. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Services** | Python 3.11+ w/ FastAPI | Modern, high-performance, async-native framework ideal for microservices. |
| **Frontend Service** | Next.js (React) | A robust framework for building the user-facing chat/analysis interface. |
| **Database** | TimescaleDB | PostgreSQL with time-series superpowers. Meets the core requirement. |
| **Vector Database** | Qdrant | High-performance vector search engine for entity resolution. |
| **Containerization** | Docker | Standard for containerizing applications for local dev and k8s deployment. |
| **Orchestration** | Kubernetes (K8s) | The target production environment. |
| **Pipeline Manager** | Prefect | A modern, Python-native workflow orchestrator. |
| **Message Queue** | RabbitMQ | A mature and reliable message broker for decoupling services in the ETL pipeline. |

### 3. Service Breakdown

1.  **Backend API Service:** A FastAPI service providing REST endpoints for:
    *   Querying property data.
    *   **Geospatial Data Ingestion:** `/api/v1/ingest-geodata` endpoint accepts zipped GDB files, extracts them, and loads them into PostGIS.
    *   Entity Resolution logic.
2.  **Web Service:** A Next.js application serving the user interface.
3.  **Entity Resolution Indexer:** A Kubernetes Job (GPU-accelerated) that generates embeddings for property records and indexes them in Qdrant.
4.  **Orchestrator (Prefect):** Manages the scheduling of data collection tasks.
5.  **Data Collectors:** Services responsible for scraping and fetching external data.

### 4. Data Model (TimescaleDB)

*   **Hypertable: `property_events`**
    *   `timestamp` (TIMESTAMPTZ, the hypertable key)
    *   `parcel_id` (TEXT)
    *   `county` (TEXT)
    *   `event_type` (TEXT)
    *   `source` (TEXT)
    *   `data` (JSONB)
*   **Standard Table: `properties`** (Geospatial)
    *   `parcel_id` (TEXT, Primary Key)
    *   `geom` (Geometry)
    *   Static info like property address, owners, tax data.

### 5. Deployment & Operations

*   **Kubernetes Namespace:** `propfinder`
*   **Database Migration:** Handled via a dedicated `migration-job` using Alembic.
*   **Ingestion Workflow:**
    1.  User uploads `.zip` containing `.gdb` via API.
    2.  Backend service extracts to temp storage.
    3.  Backend service parses GDB using `geopandas` and `GDAL`.
    4.  Data is cleaned and inserted into the `properties` table.
*   **Entity Resolution Workflow:**
    1.  `indexer-job` is triggered (manually or via orchestration).
    2.  Job reads from `properties` table.
    3.  Generates embeddings on GPU nodes.
    4.  Upserts vectors to Qdrant.

### 6. Development Workflow

*   **Local:** Docker Compose for local testing (DB, RabbitMQ).
*   **Cluster:** `make k8s-apply` to deploy to K3s.
*   **Images:** Built with `docker buildx` for `linux/amd64` and pushed to private registry.