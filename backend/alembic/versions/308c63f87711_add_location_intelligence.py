"""Add location intelligence tables

Revision ID: 308c63f87711
Revises: 16ec63f87710
Create Date: 2026-09-18 23:10:10.053528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '308c63f87711'
down_revision: Union[str, None] = '16ec63f87710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # location_enrichment_jobs
    op.create_table('location_enrichment_jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('provider_status', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_location_enrichment_jobs_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_location_enrichment_jobs'))
    )
    op.create_index(op.f('ix_location_enrichment_jobs_id'), 'location_enrichment_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_location_enrichment_jobs_project_id'), 'location_enrichment_jobs', ['project_id'], unique=False)

    # project_locations
    op.create_table('project_locations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('location_geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_project_locations_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_locations'))
    )
    op.create_index(op.f('ix_project_locations_id'), 'project_locations', ['id'], unique=False)
    op.create_index(op.f('ix_project_locations_project_id'), 'project_locations', ['project_id'], unique=True)

    # project_dam_candidates
    op.create_table('project_dam_candidates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('dam_name', sa.String(length=255), nullable=True),
    sa.Column('distance_km', sa.Float(), nullable=True),
    sa.Column('source_name', sa.String(length=100), nullable=True),
    sa.Column('source_record_id', sa.String(length=100), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_project_dam_candidates_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_dam_candidates'))
    )
    op.create_index(op.f('ix_project_dam_candidates_id'), 'project_dam_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_project_dam_candidates_project_id'), 'project_dam_candidates', ['project_id'], unique=False)

    # project_dams
    op.create_table('project_dams',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('dam_name', sa.String(length=255), nullable=True),
    sa.Column('project_identification_code', sa.String(length=100), nullable=True),
    sa.Column('operator', sa.String(length=255), nullable=True),
    sa.Column('year_completed', sa.Integer(), nullable=True),
    sa.Column('river_basin', sa.String(length=255), nullable=True),
    sa.Column('river', sa.String(length=255), nullable=True),
    sa.Column('nearest_city', sa.String(length=255), nullable=True),
    sa.Column('seismic_zone', sa.String(length=50), nullable=True),
    sa.Column('dam_type', sa.String(length=100), nullable=True),
    sa.Column('dam_height_m', sa.Float(), nullable=True),
    sa.Column('dam_length_m', sa.Float(), nullable=True),
    sa.Column('gross_storage_capacity_mcm', sa.Float(), nullable=True),
    sa.Column('reservoir_area_sq_km', sa.Float(), nullable=True),
    sa.Column('effective_storage_capacity_mcm', sa.Float(), nullable=True),
    sa.Column('purpose', sa.String(length=255), nullable=True),
    sa.Column('designed_spillway_capacity_cumec', sa.Float(), nullable=True),
    sa.Column('source_name', sa.String(length=100), nullable=True),
    sa.Column('source_url', sa.String(length=255), nullable=True),
    sa.Column('source_record_id', sa.String(length=100), nullable=True),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_project_dams_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_dams'))
    )
    op.create_index(op.f('ix_project_dams_id'), 'project_dams', ['id'], unique=False)
    op.create_index(op.f('ix_project_dams_project_id'), 'project_dams', ['project_id'], unique=True)

    # population_snapshots
    op.create_table('population_snapshots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('population_5km', sa.Integer(), nullable=True),
    sa.Column('population_10km', sa.Integer(), nullable=True),
    sa.Column('population_25km', sa.Integer(), nullable=True),
    sa.Column('source_name', sa.String(length=100), nullable=True),
    sa.Column('reference_year', sa.Integer(), nullable=True),
    sa.Column('methodology', sa.Text(), nullable=True),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_population_snapshots_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_population_snapshots'))
    )
    op.create_index(op.f('ix_population_snapshots_id'), 'population_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_population_snapshots_project_id'), 'population_snapshots', ['project_id'], unique=True)

    # water_snapshots
    op.create_table('water_snapshots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('current_water_level_m', sa.Float(), nullable=True),
    sa.Column('live_storage_mcm', sa.Float(), nullable=True),
    sa.Column('storage_percentage', sa.Float(), nullable=True),
    sa.Column('inflow_cumec', sa.Float(), nullable=True),
    sa.Column('outflow_cumec', sa.Float(), nullable=True),
    sa.Column('observation_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_name', sa.String(length=100), nullable=True),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_water_snapshots_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_water_snapshots'))
    )
    op.create_index(op.f('ix_water_snapshots_id'), 'water_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_water_snapshots_project_id'), 'water_snapshots', ['project_id'], unique=True)

def downgrade() -> None:
    pass
