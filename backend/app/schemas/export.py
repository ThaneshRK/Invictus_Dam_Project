from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from app.models.export import ExportStatus

class ExportJobCreate(BaseModel):
    result_id: uuid.UUID
    format: str = Field(..., description="Format to export: SHP, GeoJSON, GeoTIFF, CSV, KML")

class ExportJobRead(BaseModel):
    id: uuid.UUID
    result_id: uuid.UUID
    format: str
    status: ExportStatus
    metadata_: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
