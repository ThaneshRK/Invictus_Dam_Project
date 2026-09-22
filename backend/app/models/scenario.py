import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from app.db.base_class import Base

class ScenarioType(str, enum.Enum):
    DAM_BREAK = "DAM_BREAK"
    WATER_RELEASE = "WATER_RELEASE"
    RIVER_BLOCKAGE = "RIVER_BLOCKAGE"

class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scenario_type: Mapped[ScenarioType] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    source_datasets: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    simulation_duration: Mapped[float] = mapped_column(Float, nullable=False, default=24.0) # hours
    timestep: Mapped[float] = mapped_column(Float, nullable=False, default=1.0) # seconds
    output_interval: Mapped[float] = mapped_column(Float, nullable=False, default=3600.0) # seconds
    
    boundary_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project")
    
    initial_condition = relationship("InitialCondition", back_populates="scenario", uselist=False, cascade="all, delete-orphan")
    dambreak_params = relationship("DamBreakParameters", back_populates="scenario", uselist=False, cascade="all, delete-orphan")
    controlled_release_params = relationship("ControlledReleaseParameters", back_populates="scenario", uselist=False, cascade="all, delete-orphan")
    river_blockage_params = relationship("RiverBlockageParameters", back_populates="scenario", uselist=False, cascade="all, delete-orphan")

class InitialCondition(Base):
    __tablename__ = "initial_conditions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    water_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage: Mapped[float | None] = mapped_column(Float, nullable=True)
    discharge: Mapped[float | None] = mapped_column(Float, nullable=True)
    hydrograph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    scenario = relationship("Scenario", back_populates="initial_condition")

class DamBreakParameters(Base):
    __tablename__ = "dambreak_parameters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    breach_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    breach_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    breach_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    formation_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    scenario = relationship("Scenario", back_populates="dambreak_params")

class ControlledReleaseParameters(Base):
    __tablename__ = "controlled_release_parameters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    release_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    discharge_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # CONSTANT, HYDROGRAPH
    constant_discharge: Mapped[float | None] = mapped_column(Float, nullable=True)
    hydrograph_dataset_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    scenario = relationship("Scenario", back_populates="controlled_release_params")

class RiverBlockageParameters(Base):
    __tablename__ = "river_blockage_parameters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    blockage_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    blockage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    length: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    crest_elevation: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    breach_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    formation_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    scenario = relationship("Scenario", back_populates="river_blockage_params")

