from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, description="Latitude of the project area (e.g. Dam location)")
    longitude: Optional[float] = Field(None, description="Longitude of the project area (e.g. Dam location)")
    crs: Optional[str] = Field("EPSG:4326", max_length=50)
    project_type: Optional[str] = None
    selected_dam_id: Optional[str] = None
    selected_reservoir_id: Optional[str] = None
    selected_river_id: Optional[str] = None
    dem_dataset_id: Optional[str] = None
    location_source: Optional[str] = None
    location_reference: Optional[str] = None
    data_readiness_status: Optional[float] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crs: Optional[str] = Field(None, max_length=50)
    project_type: Optional[str] = None
    selected_dam_id: Optional[str] = None
    selected_reservoir_id: Optional[str] = None
    selected_river_id: Optional[str] = None
    dem_dataset_id: Optional[str] = None
    location_source: Optional[str] = None
    location_reference: Optional[str] = None
    data_readiness_status: Optional[float] = None

class ProjectRead(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
