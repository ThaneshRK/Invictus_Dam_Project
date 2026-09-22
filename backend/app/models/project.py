import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from app.db.base_class import Base

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Coordinates of the dam / area of interest
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Study area geometry, typically a Polygon or MultiPolygon. 
    # SRID 4326 is standard WGS84, but can be updated.
    study_area: Mapped[str | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    crs: Mapped[str | None] = mapped_column(String(50), nullable=True, default="EPSG:4326")
    
    # New Wizard Fields
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    location_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    selected_dam_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    selected_reservoir_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    selected_river_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    dem_dataset_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_readiness_status: Mapped[float | None] = mapped_column(Float, nullable=True)

    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
