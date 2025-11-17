# TECHNICAL SPECIFICATION
### WI-RE Analysis Platform - v1.0

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
        B --> E[Query Service<br>(FastAPI)];
    end

    subgraph Data Plane
        F[TimescaleDB<br>(PostgreSQL)]
        G[Message Queue<br>(RabbitMQ)]
    end

    subgraph Data Pipeline
        H[ETL Transformation Service]
        I[Data Collectors / Workers]
    end

    C -- REST API --> E;
    D -- Triggers Jobs --> G;
    E -- SQL Queries --> F;

    G -- Pub/Sub --> H;
    G -- Pub/Sub --> I;

    H -- Inserts Events --> F;
    I -- Publishes Raw Data --> G;

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```

### 2. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Services** | Python 3.11+ w/ FastAPI | Modern, high-performance, async-native framework ideal for microservices. |
| **Frontend Service** | Next.js (React) | A robust framework for building the user-facing chat/analysis interface. |
| **Database** | TimescaleDB | PostgreSQL with time-series superpowers. Meets the core requirement. |
| **Containerization** | Docker | Standard for containerizing applications for local dev and k8s deployment. |
| **Orchestration** | Kubernetes (K8s) | The target production environment. |
| **Pipeline Manager** | Prefect | A modern, Python-native workflow orchestrator. Easier to start with than Airflow. |
| **API Gateway** | Traefik | K8s-native ingress controller, excellent for routing and service discovery. |
| **Message Queue** | RabbitMQ | A mature and reliable message broker for decoupling services in the ETL pipeline. |

### 3. Service Breakdown

1.  **Web Service:** A Next.js application serving the user interface. This is where the "chat agent" experience will live. It will communicate with the backend via the API Gateway.
2.  **Query Service:** A FastAPI service providing a REST API for querying the database. It will contain all the business logic for filtering, aggregation, and generating property summaries.
3.  **Orchestrator (Prefect):** Manages the scheduling of all data collection and processing tasks. It will trigger jobs like "Fetch RETR data monthly" or "Scrape Vilas County tax data weekly".
4.  **Data Collectors:** A set of services responsible for *extraction*. These are the workers that download bulk data, scrape websites, or connect to future APIs. They will be designed to be modular.
5.  **Transformation Service:** A service that subscribes to messages from the Data Collectors (via RabbitMQ). It will be responsible for cleaning, normalizing, and linking data before loading it into TimescaleDB.
6.  **RAG Export Service:** A dedicated service that, when triggered, will query the database (via the Query Service) and generate the structured `.txt` files for LLM analysis.

### 4. Data Model (TimescaleDB)

We will stick to the event-based model.

*   **Hypertable: `property_events`**
    *   `timestamp` (TIMESTAMPTZ, the hypertable key)
    *   `parcel_id` (TEXT)
    *   `county` (TEXT)
    *   `event_type` (TEXT, e.g., 'sale', 'tax_status_change', 'owner_change')
    *   `source` (TEXT, e.g., 'RETR_monthly_zip', 'vilas_county_scraper_v1')
    *   `data` (JSONB, a flexible field for all event-specific data)
*   **Standard Table: `parcels`**
    *   `parcel_id` (TEXT, Primary Key)
    *   `county` (TEXT)
    *   Static info like property address, geometry data, etc.

### 5. Key Concepts & Implementation Details

*   **AI-Powered Scraper Modules:**
    *   We will define a Python `ScraperInterface` class with required methods like `connect()`, `fetch_data()`, and `get_source_name()`.
    *   Each county-specific scraper will be a separate Python file that implements this interface.
    *   The Data Collector service will be configured to dynamically load these modules from a specific directory in its container.
    *   **Your Workflow:** You can use an LLM to generate the Python code for a new scraper. You then save that file, rebuild the Data Collector image, and the new scraper becomes available to the Orchestrator.

*   **Cross-Platform Development (M3 ARM -> Xeon x86):**
    *   This is a solved problem with Docker. We will use `docker buildx` to build multi-platform images (`linux/amd64` and `linux/arm64`). This ensures the images you build on your Mac will run flawlessly on the Xeon Kubernetes cluster.

*   **Backup and Restore:**
    *   We will create a Kubernetes `CronJob`.
    *   This job will run a container with `pg_dump` on a schedule (e.g., nightly) to back up the TimescaleDB database.
    *   The backup files will be stored on a Persistent Volume (PV) or, even better, pushed to an external S3-compatible object store for disaster recovery.
