import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy import String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base_class import Base

# Database Model
class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    engine_used: Mapped[str] = mapped_column(String(100), nullable=False)
    crs: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Store references to output artifacts (raster files, not massive DB arrays)
    outputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Aggregated Stats
    inundated_area_km2: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_depth_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_depth_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_velocity_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# Pydantic Schemas
class ResultRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scenario_id: uuid.UUID
    engine_used: str
    crs: str
    outputs: Dict[str, Any]
    inundated_area_km2: Optional[float]
    max_depth_m: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True
