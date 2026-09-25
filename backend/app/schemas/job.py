from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from app.models.job import JobStatus

class SimulationJobCreate(BaseModel):
    project_id: uuid.UUID
    scenario_id: uuid.UUID
    engine: str
    operation: str = "SIMULATION"

class SimulationJobRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scenario_id: uuid.UUID
    engine: str
    operation: str
    status: JobStatus
    progress: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    result_references: Optional[Dict[str, Any]] = None
    input_snapshot: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class JobStatusResponse(BaseModel):
    status: JobStatus
    progress: float
    error: Optional[str] = None
