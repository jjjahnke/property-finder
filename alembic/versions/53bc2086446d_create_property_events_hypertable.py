"""create property_events hypertable

Revision ID: 53bc2086446d
Revises: 
Create Date: 2025-11-17 12:42:07.223523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = '53bc2086446d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        # Core Identifiers
        sa.Column('STATEID', sa.Text(), nullable=True),
        sa.Column('PARCELID', sa.Text(), nullable=False),
        sa.Column('TAXPARCELID', sa.Text(), nullable=True),
        sa.Column('PARCELDATE', sa.Date(), nullable=True),
        sa.Column('TAXROLLYEAR', sa.Numeric(), nullable=True),
        sa.Column('OWNERNME1', sa.Text(), nullable=True),
        sa.Column('OWNERNME2', sa.Text(), nullable=True),
        # Address Information
        sa.Column('PSTLADRESS', sa.Text(), nullable=True),
        sa.Column('SITEADRESS', sa.Text(), nullable=True),
        sa.Column('ADDNUMPREFIX', sa.Text(), nullable=True),
        sa.Column('ADDNUM', sa.Text(), nullable=True),
        sa.Column('ADDNUMSUFFIX', sa.Text(), nullable=True),
        sa.Column('PREFIX', sa.Text(), nullable=True),
        sa.Column('STREETNAME', sa.Text(), nullable=True),
        sa.Column('STREETTYPE', sa.Text(), nullable=True),
        sa.Column('SUFFIX', sa.Text(), nullable=True),
        sa.Column('LANDMARKNAME', sa.Text(), nullable=True),
        sa.Column('UNITTYPE', sa.Text(), nullable=True),
        sa.Column('UNITID', sa.Text(), nullable=True),
        sa.Column('PLACENAME', sa.Text(), nullable=True),
        sa.Column('ZIPCODE', sa.Text(), nullable=True),
        sa.Column('ZIP4', sa.Text(), nullable=True),
        sa.Column('STATE', sa.Text(), nullable=True),
        # School District
        sa.Column('SCHOOLDIST', sa.Text(), nullable=True),
        sa.Column('SCHOOLDISTNO', sa.Text(), nullable=True),
        # Assessed Values
        sa.Column('CNTASSDVALUE', sa.Numeric(), nullable=True),
        sa.Column('LNDVALUE', sa.Numeric(), nullable=True),
        sa.Column('IMPVALUE', sa.Numeric(), nullable=True),
        sa.Column('MFLVALUE', sa.Numeric(), nullable=True),
        sa.Column('ESTFMKVALUE', sa.Numeric(), nullable=True),
        sa.Column('NETPRPTA', sa.Numeric(), nullable=True),
        sa.Column('GRSPRPTA', sa.Numeric(), nullable=True),
        # Property Class
        sa.Column('PROPCLASS', sa.Text(), nullable=True),
        sa.Column('AUXCLASS', sa.Text(), nullable=True),
        # Acreage
        sa.Column('ASSDACRES', sa.Float(), nullable=True),
        sa.Column('DEEDACRES', sa.Float(), nullable=True),
        sa.Column('GISACRES', sa.Float(), nullable=True),
        # Metadata
        sa.Column('CONAME', sa.Text(), nullable=True),
        sa.Column('LOADDATE', sa.Date(), nullable=True),
        sa.Column('PARCELFIPS', sa.Text(), nullable=True),
        sa.Column('PARCELSRC', sa.Text(), nullable=True),
        # Coordinates
        sa.Column('LONGITUDE', sa.Float(), nullable=True),
        sa.Column('LATITUDE', sa.Float(), nullable=True),
        # Shape Info
        sa.Column('Shape_Length', sa.Float(), nullable=True),
        sa.Column('Shape_Area', sa.Float(), nullable=True),
        # Geometry
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('STATEID')
    )
    op.create_table(
        'property_events',
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('STATEID', sa.Text(), nullable=False), # Foreign key to properties.STATEID
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        
        # Discovered Event Columns
        sa.Column('SaleNumber', sa.Text(), nullable=True),
        sa.Column('YearCaptured', sa.Integer(), nullable=True),
        sa.Column('GrantorType', sa.Text(), nullable=True),
        sa.Column('GrantorGranteeRelationship', sa.Text(), nullable=True),
        sa.Column('WeatherStds', sa.Text(), nullable=True),
        sa.Column('EnergyExclusion', sa.Text(), nullable=True),
        sa.Column('Section', sa.Text(), nullable=True),
        sa.Column('Township', sa.Text(), nullable=True),
        sa.Column('Range', sa.Text(), nullable=True),
        sa.Column('PropertyType', sa.Text(), nullable=True),
        sa.Column('PredominateUse', sa.Text(), nullable=True),
        sa.Column('MultiFamilyUnits', sa.Integer(), nullable=True),
        sa.Column('AgrOwnerLessThan5years', sa.Text(), nullable=True),
        sa.Column('TotalAcres', sa.Float(), nullable=True),
        sa.Column('WaterFrontIndicator', sa.Text(), nullable=True),
        sa.Column('TransferType', sa.Text(), nullable=True),
        sa.Column('OwnerInterestTransferred', sa.Text(), nullable=True),
        sa.Column('GrantorRightsRetained', sa.Text(), nullable=True),
        sa.Column('PersPropertyValueExcluded', sa.Numeric(), nullable=True),
        sa.Column('PersPropertyValueExempt', sa.Numeric(), nullable=True),
        sa.Column('TotalRealEstateValue', sa.Numeric(), nullable=True),
        sa.Column('TransferFee', sa.Numeric(), nullable=True),
        sa.Column('TransferExemptionNumber', sa.Text(), nullable=True),
        sa.Column('FinancingCode', sa.Text(), nullable=True),
        sa.Column('DocumentNumber', sa.Text(), nullable=True),
        sa.Column('DateRecorded', sa.Date(), nullable=True),
        sa.Column('DateConveyed', sa.Date(), nullable=True),
        sa.Column('DeedDate', sa.Date(), nullable=True),
        sa.Column('ConveyanceCode', sa.Text(), nullable=True),
        sa.Column('ParcelIdentification', sa.Text(), nullable=True),
        sa.Column('MultiGrantors', sa.Text(), nullable=True),
        sa.Column('GrantorLastName', sa.Text(), nullable=True),
        sa.Column('GrantorFirstName', sa.Text(), nullable=True),
        sa.Column('GrantorStreetNumber', sa.Text(), nullable=True),
        sa.Column('GrantorAddress', sa.Text(), nullable=True),
        sa.Column('GrantorCity', sa.Text(), nullable=True),
        sa.Column('GrantorState', sa.Text(), nullable=True),
        sa.Column('GrantorZip', sa.Text(), nullable=True),
        sa.Column('CertificationDate', sa.Date(), nullable=True),
        sa.Column('MultiGrantees', sa.Text(), nullable=True),
        sa.Column('GranteeLastName', sa.Text(), nullable=True),
        sa.Column('GranteeFirstName', sa.Text(), nullable=True),
        sa.Column('GranteeStreetNumber', sa.Text(), nullable=True),
        sa.Column('GranteeAddress', sa.Text(), nullable=True),
        sa.Column('GranteeCity', sa.Text(), nullable=True),
        sa.Column('GranteeState', sa.Text(), nullable=True),
        sa.Column('GranteeZip', sa.Text(), nullable=True),
        sa.Column('GranteeCertificationDate', sa.Date(), nullable=True),
        sa.Column('GranteePrimaryResidence', sa.Text(), nullable=True),
        sa.Column('TaxBillGrantee', sa.Text(), nullable=True),
        sa.Column('CityYN', sa.Text(), nullable=True),
        sa.Column('VillageYN', sa.Text(), nullable=True),
        sa.Column('TownYN', sa.Text(), nullable=True),
        sa.Column('TVCname', sa.Text(), nullable=True),
        sa.Column('CountyName', sa.Text(), nullable=True),
        sa.Column('PropertyAddress', sa.Text(), nullable=True),
        sa.Column('LotSize1', sa.Float(), nullable=True),
        sa.Column('LotSize', sa.Float(), nullable=True),
        sa.Column('ManagedForestLandAcres', sa.Float(), nullable=True),
        sa.Column('VolumeJacket', sa.Text(), nullable=True),
        sa.Column('PageImage', sa.Text(), nullable=True),
        sa.Column('SplitParcel', sa.Text(), nullable=True),
        sa.Column('AgentFor', sa.Text(), nullable=True),
        sa.Column('AgentName', sa.Text(), nullable=True),
        sa.Column('AgentStreet', sa.Text(), nullable=True),
        sa.Column('AgentAddress', sa.Text(), nullable=True),
        sa.Column('AgentCity', sa.Text(), nullable=True),
        sa.Column('AgentState', sa.Text(), nullable=True),
        sa.Column('AgentZip', sa.Text(), nullable=True),
        sa.Column('PreparerName', sa.Text(), nullable=True),
        sa.Column('GrantorTypeOtherNote', sa.Text(), nullable=True),
        sa.Column('GrantorGranteeRelationOther', sa.Text(), nullable=True),
        sa.Column('TaxBillName', sa.Text(), nullable=True),
        sa.Column('TaxBillStreetNumber', sa.Text(), nullable=True),
        sa.Column('TaxBillAddress', sa.Text(), nullable=True),
        sa.Column('TaxBillCity', sa.Text(), nullable=True),
        sa.Column('TaxBillState', sa.Text(), nullable=True),
        sa.Column('TaxBillZip', sa.Text(), nullable=True),
        sa.Column('W12documentNumber', sa.Text(), nullable=True),
        sa.Column('PropertyTypeOtherNote', sa.Text(), nullable=True),
        sa.Column('MiscUseNote', sa.Text(), nullable=True),
        sa.Column('TransferTypeOtherNote', sa.Text(), nullable=True),
        sa.Column('OwnerInterestOtherNote', sa.Text(), nullable=True),
        sa.Column('GrantorRightsOtherNotes', sa.Text(), nullable=True),
        sa.Column('PreviousDocumentNumber', sa.Text(), nullable=True),
        sa.Column('ConveyanceCodeOtherNote', sa.Text(), nullable=True),
        sa.Column('MiscCountyTVC', sa.Text(), nullable=True),
        sa.Column('MultiTVSs', sa.Text(), nullable=True),
        sa.Column('WaterFrontFeet', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('event_id', 'event_date')
    )
    op.execute("SELECT create_hypertable('property_events', 'event_date');")
    op.create_foreign_key('fk_property_events_stateid', 'property_events', 'properties', ['STATEID'], ['STATEID'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_property_events_parcel_id', 'property_events', type_='foreignkey')
    op.drop_table('property_events')
    op.drop_table('properties')
    op.execute("DROP EXTENSION IF EXISTS postgis;")
