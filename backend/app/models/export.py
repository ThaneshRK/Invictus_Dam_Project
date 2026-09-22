import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base_class import Base

class ExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    
    format: Mapped[str] = mapped_column(String(50), nullable=False) # SHP, GeoJSON, GeoTIFF, CSV, KML
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ExportStatus] = mapped_column(String(50), nullable=False, default=ExportStatus.PENDING)
    
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    result: Mapped["SimulationResult"] = relationship("SimulationResult")
