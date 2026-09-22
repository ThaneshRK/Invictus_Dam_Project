import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base_class import Base

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class SimulationJob(Base):
    """Unified background simulation job tracker"""
    __tablename__ = "simulation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    engine: Mapped[str] = mapped_column(String(50), nullable=False) # SPH, DELFT3D
    operation: Mapped[str] = mapped_column(String(50), nullable=False) # SIMULATION, PREPROCESSING
    
    status: Mapped[JobStatus] = mapped_column(String(50), nullable=False, default=JobStatus.QUEUED)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Store references to output results if completed
    result_references: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project")
    scenario: Mapped["Scenario"] = relationship("Scenario")
