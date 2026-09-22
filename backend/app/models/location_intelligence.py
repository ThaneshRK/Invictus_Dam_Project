import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from app.db.base_class import Base

class LocationEnrichmentJob(Base):
    __tablename__ = "location_enrichment_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, PARTIAL, FAILED
    
    # Store provider-specific errors or statuses here
    provider_status: Mapped[dict | None] = mapped_column(JSONB, nullable=True) 
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ProjectLocation(Base):
    __tablename__ = "project_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # SRID 4326 PostGIS Point
    location_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ProjectDamCandidate(Base):
    __tablename__ = "project_dam_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    
    dam_name: Mapped[str | None] = mapped_column(String(255))
    distance_km: Mapped[float | None] = mapped_column(Float)
    
    source_name: Mapped[str | None] = mapped_column(String(100))
    source_record_id: Mapped[str | None] = mapped_column(String(100))
    
    # Basic metadata to display in list
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ProjectDam(Base):
    """The selected dam for a project."""
    __tablename__ = "project_dams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    
    dam_name: Mapped[str | None] = mapped_column(String(255))
    project_identification_code: Mapped[str | None] = mapped_column(String(100))
    operator: Mapped[str | None] = mapped_column(String(255))
    year_completed: Mapped[int | None] = mapped_column(Integer)
    river_basin: Mapped[str | None] = mapped_column(String(255))
    river: Mapped[str | None] = mapped_column(String(255))
    nearest_city: Mapped[str | None] = mapped_column(String(255))
    seismic_zone: Mapped[str | None] = mapped_column(String(50))
    dam_type: Mapped[str | None] = mapped_column(String(100))
    
    dam_height_m: Mapped[float | None] = mapped_column(Float)
    dam_length_m: Mapped[float | None] = mapped_column(Float)
    gross_storage_capacity_mcm: Mapped[float | None] = mapped_column(Float)
    reservoir_area_sq_km: Mapped[float | None] = mapped_column(Float)
    effective_storage_capacity_mcm: Mapped[float | None] = mapped_column(Float)
    purpose: Mapped[str | None] = mapped_column(String(255))
    designed_spillway_capacity_cumec: Mapped[float | None] = mapped_column(Float)

    # Source Attribution
    source_name: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(255))
    source_record_id: Mapped[str | None] = mapped_column(String(100))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PopulationSnapshot(Base):
    __tablename__ = "population_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    
    population_5km: Mapped[int | None] = mapped_column(Integer)
    population_10km: Mapped[int | None] = mapped_column(Integer)
    population_25km: Mapped[int | None] = mapped_column(Integer)
    
    # Source Attribution
    source_name: Mapped[str | None] = mapped_column(String(100))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    methodology: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WaterSnapshot(Base):
    __tablename__ = "water_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    
    current_water_level_m: Mapped[float | None] = mapped_column(Float)
    live_storage_mcm: Mapped[float | None] = mapped_column(Float)
    storage_percentage: Mapped[float | None] = mapped_column(Float)
    inflow_cumec: Mapped[float | None] = mapped_column(Float)
    outflow_cumec: Mapped[float | None] = mapped_column(Float)
    
    # Source Attribution
    observation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_name: Mapped[str | None] = mapped_column(String(100))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
