# WI-RE Analysis Platform

This project builds a platform for analyzing property data, leveraging TimescaleDB for event tracking and Qdrant for entity resolution.

## Getting Started

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd property-finder
    ```

2.  **Set up the Python virtual environment:**
    ```bash
    make setup
    ```

3.  **Start Local Services (Docker Compose):**
    ```bash
    make up
    ```

4.  **Apply Migrations:**
    ```bash
    make migrate
    ```

### Kubernetes Deployment (K3s)

1.  **Prerequisites:** A K3s cluster with GPU nodes (optional for backend, required for indexer).

2.  **Deploy Infrastructure:**
    ```bash
    make k8s-apply
    ```
    This deploys Postgres (TimescaleDB), Qdrant, and the Backend API service to the `propfinder` namespace.

3.  **Run Migrations in Cluster:**
    A migration job is included in the manifests, but can be triggered manually:
    ```bash
    kubectl delete job migration-job -n propfinder
    kubectl apply -f k8s/migration-job.yaml -n propfinder
    ```

4.  **Access the API:**
    The backend service is exposed via `LoadBalancer`. Find the URL:
    ```bash
    kubectl get service backend-service -n propfinder
    ```
    Access documentation at `http://<NODE-IP>:<PORT>/docs`.

### Geospatial Data Ingestion

To ingest parcel data (GDB format):

1.  Zip your `.gdb` directory (e.g., `parcels.zip` containing `MyParcels.gdb`).
2.  Go to the API Swagger UI (`/docs`).
3.  Use the `POST /api/v1/ingest-geodata` endpoint to upload the zip file.
4.  The service will process the file and load it into the database.
