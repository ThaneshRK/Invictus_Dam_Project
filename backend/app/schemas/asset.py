from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

class Dam3DAssetBase(BaseModel):
    project_id: uuid.UUID
    file_path: str
    asset_format: str = "GLB"
    origin_lat: float = 0.0
    origin_lon: float = 0.0
    origin_elevation: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0
    source: Optional[str] = None
    units: str = "meters"
    coordinate_reference_system: Optional[str] = None

class Dam3DAssetCreate(Dam3DAssetBase):
    pass

class Dam3DAssetUpdate(BaseModel):
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    origin_elevation: Optional[float] = None
    rotation_x: Optional[float] = None
    rotation_y: Optional[float] = None
    rotation_z: Optional[float] = None
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    scale_z: Optional[float] = None
    coordinate_reference_system: Optional[str] = None

class Dam3DAssetRead(Dam3DAssetBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
