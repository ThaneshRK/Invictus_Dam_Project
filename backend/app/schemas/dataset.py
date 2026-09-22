from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from app.models.dataset import DatasetCategory

class DatasetBase(BaseModel):
    name: str = Field(..., max_length=255)
    dataset_type: DatasetCategory

class DatasetCreate(DatasetBase):
    pass

class DatasetRead(DatasetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    file_path: str
    format: str
    crs: Optional[str] = None
    resolution: Optional[float] = None
    size: Optional[float] = None
    metadata_: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
