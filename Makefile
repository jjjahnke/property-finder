.PHONY: all setup run test lint up down migrate revision clean

# ==============================================================================
# Main Targets
# ==============================================================================

all: setup

setup: .venv/bin/activate

run: .venv/bin/activate
	@echo "Running the application (placeholder)"
	# ./venv/bin/uvicorn app.main:app --reload


test: .venv/bin/activate
	@echo "Running tests (placeholder)"
	# ./venv/bin/pytest

lint: .venv/bin/activate
	@echo "Linting code (placeholder)"
	# ./venv/bin/pyright .
	# ./venv/bin/black . --check

# ==============================================================================
# Docker & Database
# ==============================================================================

up:
	@echo "Starting Docker services..."
	docker-compose up -d

down:
	@echo "Stopping and removing Docker services..."
	docker-compose down -v

migrate: .venv/bin/activate
	@echo "Waiting for database to start..."
	sleep 5
	@echo "Applying database migrations..."
	./.venv/bin/alembic upgrade head

revision: .venv/bin/activate
	@[ -z "$(m)" ] && echo "Usage: make revision m=\"your migration message\"" && exit 1 || \
	echo "Creating new migration: $(m)"
	./.venv/bin/alembic revision -m "$(m)"

build:
	@echo "Building Docker images..."
	docker-compose build

ingest-geo:
	@echo "Running geospatial data ingestion script in Docker..."
	docker-compose run --rm backend python ingest_geodata.py

ingest-events:
	@echo "Running event data ingestion script in Docker..."
	docker-compose run --rm backend python ingest_events.py

match-parcels:
	@echo "Running parcel matching script with LLM in Docker..."
	docker-compose run --rm backend python scripts/match_parcels_llm.py

# Phony targets
.PHONY: all up down logs backend test migrate ingest-geo ingest-events match-parcels
	@echo "Discovering geospatial data columns..."
	docker-compose run --rm backend python scripts/discover_geo_columns.py

discover-event-columns:
	@echo "Discovering event data columns..."
	docker-compose run --rm backend python scripts/discover_event_columns.py

verify-file-completeness:
	@echo "Verifying event file completeness..."
	docker-compose run --rm backend python scripts/verify_file_completeness.py

# ==============================================================================
# Setup & Cleanup
# ==============================================================================

.venv/bin/activate: requirements.txt
	@echo "Creating Python virtual environment and installing dependencies"
	python3 -m venv .venv
	./.venv/bin/pip install -r requirements.txt
	touch .venv/bin/activate

clean:
	@echo "Cleaning up"
	rm -rf .venv
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete