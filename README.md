# WI-RE Analysis Platform

This project aims to build a platform for analyzing property data, starting with Wisconsin Department of Revenue (RETR) sales data.

## Getting Started

To set up the development environment and get the database running, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd property-finder
    ```

2.  **Set up the Python virtual environment and install dependencies:**
    ```bash
    make setup
    ```

3.  **Start the Docker services (TimescaleDB, RabbitMQ, Backend):**
    Ensure Docker Desktop is running.
    ```bash
    make up
    ```

4.  **Apply database migrations:**
    ```bash
    make migrate
    ```

    To create a new migration, use:
    ```bash
    make revision m="your migration message"
    ```

Further instructions will be added here as the project progresses.