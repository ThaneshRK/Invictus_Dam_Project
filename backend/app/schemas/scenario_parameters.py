from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List, Union

class DamBreakParameters(BaseModel):
    initial_water_level: float = Field(..., description="Initial water level in meters")
    reservoir_volume: float = Field(..., ge=0, description="Volume of the reservoir in cubic meters")
    breach_width: float = Field(..., gt=0, description="Width of the breach in meters")
    breach_height: float = Field(..., gt=0, description="Height of the breach in meters")
    breach_elevation: float = Field(..., description="Elevation of the breach bottom in meters")
    breach_formation_time: float = Field(..., gt=0, description="Time taken for the breach to form fully in hours")
    initial_downstream_condition: float = Field(0.0, description="Initial water depth downstream in meters")

class WaterReleaseParameters(BaseModel):
    initial_water_level: float = Field(..., description="Initial water level in meters")
    initial_discharge: float = Field(0.0, ge=0, description="Initial discharge in cubic meters per second")
    peak_discharge: float = Field(..., gt=0, description="Peak discharge in cubic meters per second")
    release_duration: float = Field(..., gt=0, description="Duration of the release in hours")
    release_curve: Optional[List[dict]] = Field(None, description="Time series array of dicts with 'time' and 'discharge'")

    @model_validator(mode='after')
    def check_peak_discharge(self) -> 'WaterReleaseParameters':
        if self.initial_discharge > self.peak_discharge:
            raise ValueError("Initial discharge cannot be greater than peak discharge")
        return self

class RiverBlockageParameters(BaseModel):
    blockage_height: float = Field(..., gt=0, description="Height of the blockage in meters")
    blockage_volume: float = Field(..., gt=0, description="Volume of the blockage in cubic meters")
    failure_time: float = Field(..., ge=0, description="Time at which the blockage fails in hours")
    breach_width: Optional[float] = Field(None, gt=0)
    breach_formation_time: Optional[float] = Field(None, gt=0)

ScenarioParameterUnion = Union[DamBreakParameters, WaterReleaseParameters, RiverBlockageParameters]
