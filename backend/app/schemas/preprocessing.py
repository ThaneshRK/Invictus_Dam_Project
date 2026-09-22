from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from app.models.preprocessing import JobStatus

class PreprocessingJobBase(BaseModel):
    task_type: str = Field(..., max_length=100)
    parameters: Optional[Dict[str, Any]] = None

class PreprocessingJobCreate(PreprocessingJobBase):
    pass

class PreprocessingJobRead(PreprocessingJobBase):
    id: uuid.UUID
    project_id: uuid.UUID
    status: JobStatus
    metadata_: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
