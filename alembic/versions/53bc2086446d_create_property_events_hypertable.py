"""create property_events hypertable

Revision ID: 53bc2086446d
Revises: 
Create Date: 2025-11-17 12:42:07.223523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53bc2086446d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("""
    CREATE TABLE properties (
        id SERIAL PRIMARY KEY,
        parcel_id VARCHAR(255) UNIQUE NOT NULL,
        address TEXT,
        city VARCHAR(100),
        state VARCHAR(2),
        zip_code VARCHAR(10),
        geom GEOMETRY(Point, 4326),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)
    op.execute("""
    CREATE TABLE property_events (
        event_id SERIAL,
        parcel_id VARCHAR(255) NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        event_date TIMESTAMPTZ NOT NULL,
        data JSONB,
        source VARCHAR(255),
        PRIMARY KEY (event_id, event_date)
    );
    """)
    op.execute("SELECT create_hypertable('property_events', 'event_date');")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE property_events;")
    op.execute("DROP TABLE properties;")
    op.execute("DROP EXTENSION IF EXISTS postgis;")
