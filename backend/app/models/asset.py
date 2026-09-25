import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base

class Dam3DAsset(Base):
    __tablename__ = "dam_3d_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    asset_format: Mapped[str] = mapped_column(String(10), default="GLB", nullable=False)
    
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin_lon: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin_elevation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    rotation_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    scale_x: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    scale_y: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    scale_z: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    units: Mapped[str] = mapped_column(String(50), nullable=False, default="meters")
    coordinate_reference_system: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project", backref="dam_3d_assets")
