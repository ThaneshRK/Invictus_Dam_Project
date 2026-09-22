import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base_class import Base

class HADRAnalysis(Base):
    """
    Humanitarian Assistance and Disaster Relief Exposure Analysis
    """
    __tablename__ = "hadr_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # E.g. {"buildings": "dataset_id_1", "population": "dataset_id_2"}
    exposure_datasets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # E.g. {"affected_buildings": 120, "exposed_population": 4500, "affected_road_km": 12.4}
    # Per requirements, strictly NO monetary damage invention.
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project")
    result: Mapped["SimulationResult"] = relationship("SimulationResult")
