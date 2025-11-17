"""add foreign key to property_events

Revision ID: 918f153ab74d
Revises: 53bc2086446d
Create Date: 2025-11-17 12:54:26.142859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '918f153ab74d'
down_revision: Union[str, Sequence[str], None] = '53bc2086446d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE property_events ADD CONSTRAINT fk_property_events_parcel_id FOREIGN KEY (parcel_id) REFERENCES properties (parcel_id);")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE property_events DROP CONSTRAINT fk_property_events_parcel_id;")
