from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
from app.models.scenario import ScenarioType
from app.schemas.scenario_parameters import DamBreakParameters, WaterReleaseParameters, RiverBlockageParameters, ScenarioParameterUnion

class ScenarioBase(BaseModel):
    name: str = Field(..., max_length=255)
    scenario_type: ScenarioType
    description: Optional[str] = None
    source_datasets: Optional[List[uuid.UUID]] = None
    parameters: Optional[dict] = None # Migrating to normalized tables
    
    simulation_duration: float = Field(..., gt=0, description="Simulation duration in hours")
    timestep: float = Field(..., gt=0, description="Timestep in seconds")
    output_interval: float = Field(..., gt=0, description="Output interval in seconds")
    boundary_conditions: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def check_timestep_duration(self) -> 'ScenarioBase':
        # convert duration from hours to seconds
        duration_s = self.simulation_duration * 3600
        if self.timestep > duration_s:
            raise ValueError("Timestep cannot be larger than the simulation duration")
        if self.output_interval < self.timestep:
            raise ValueError("Output interval cannot be smaller than timestep")
        return self

class ScenarioCreate(ScenarioBase):
    pass

class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    parameters: Optional[dict] = None
    simulation_duration: Optional[float] = Field(None, gt=0)
    timestep: Optional[float] = Field(None, gt=0)
    output_interval: Optional[float] = Field(None, gt=0)
    boundary_conditions: Optional[Dict[str, Any]] = None

class ScenarioRead(ScenarioBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
