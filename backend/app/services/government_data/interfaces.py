import abc
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel

class TerrainDataset(BaseModel):
    source_provider: str
    source_dataset: str
    source_url: str
    acquisition_timestamp: str
    original_crs: str
    simulation_crs: str
    resolution: float
    bounds: Tuple[float, float, float, float]
    vertical_units: str
    nodata: float
    local_file: str

class DEMProvider(abc.ABC):
    @abc.abstractmethod
    def get_provider_name(self) -> str:
        pass
        
    @abc.abstractmethod
    async def discover_dem(self, bbox_wgs84: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Returns metadata about available DEM covering the bbox."""
        pass
        
    @abc.abstractmethod
    async def acquire_dem(self, bbox_wgs84: Tuple[float, float, float, float], target_crs: str, output_dir: str) -> TerrainDataset:
        """Downloads, mosaics, reprojects, and crops the DEM."""
        pass

class HydrologyDataset(BaseModel):
    source_provider: str
    source_dataset: str
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    reservoir: Optional[str] = None
    river: Optional[str] = None
    parameter: str # e.g. "reservoir_level", "discharge"
    units_normalized: str
    timestamp: str
    value: Optional[float] = None
    source_url: str
    acquisition_timestamp: str
    
    # Provenance and source classification fields
    source_agency: Optional[str] = None
    observation_type: Optional[str] = "OBSERVATION" # OBSERVATION, FORECAST, HISTORICAL_REFERENCE
    original_value: Optional[float] = None
    original_unit: Optional[str] = None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    is_live: bool = False
    is_synthetic: bool = False
    source_type: str = "GOVERNMENT_STATIC_FIXTURE" # GOVERNMENT_STATIC_FIXTURE, GOVERNMENT_LIVE_API, OPERATOR_STATIC_FIXTURE, OPERATOR_LIVE_API, SYNTHETIC_TEST_DATA
    availability: str = "AVAILABLE" # AVAILABLE, NOT_PROVIDED

class HydrologyProvider(abc.ABC):
    @abc.abstractmethod
    def get_provider_name(self) -> str:
        pass
        
    @abc.abstractmethod
    async def get_reservoir_level(self, reservoir_name: str, dam_name: str, timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        pass
        
    @abc.abstractmethod
    async def get_river_discharge(self, river_name: str, coordinates: Tuple[float, float], timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        pass
