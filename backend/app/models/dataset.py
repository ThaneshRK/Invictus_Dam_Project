import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from app.db.base_class import Base

class DatasetCategory(str, enum.Enum):
    DEM = "DEM"
    river = "river"
    dam = "dam"
    blockage = "blockage"
    hydrological = "hydrological"
    satellite = "satellite"
    exposure = "exposure"

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_type: Mapped[DatasetCategory] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., GeoTIFF, GeoJSON, CSV
    
    crs: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Bounding box of the dataset
    bounding_box: Mapped[str | None] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)
    resolution: Mapped[float | None] = mapped_column(Float, nullable=True)
    size: Mapped[float | None] = mapped_column(Float, nullable=True) # Size in MB
    
    # Flexible metadata field for raster bands, csv columns, etc.
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    project: Mapped["Project"] = relationship("Project", back_populates="datasets")
