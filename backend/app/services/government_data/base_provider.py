import abc
from typing import Dict, Any, List, Optional, Tuple

class GovernmentDamProvider(abc.ABC):
    @abc.abstractmethod
    async def find_nearby_dams(self, latitude: float, longitude: float, radius_km: float) -> List[Dict[str, Any]]:
        pass
        
    @abc.abstractmethod
    async def get_dam_details(self, dam_identifier: str) -> Dict[str, Any]:
        pass

class PopulationProvider(abc.ABC):
    @abc.abstractmethod
    async def get_population(self, latitude: float, longitude: float, radii_km: List[float]) -> Dict[str, Any]:
        pass
        
    @abc.abstractmethod
    async def get_population_by_bbox(self, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Fetch population within a bounding box (min_lon, min_lat, max_lon, max_lat)."""
        pass

class InfrastructureProvider(abc.ABC):
    @abc.abstractmethod
    async def get_infrastructure_by_bbox(self, bbox: Tuple[float, float, float, float], infrastructure_type: str) -> Dict[str, Any]:
        """
        Fetch infrastructure (buildings, roads, facilities) within a bounding box.
        Returns GeoJSON FeatureCollection.
        infrastructure_type: 'buildings', 'roads', 'facilities'
        """
        pass

class WaterDataProvider(abc.ABC):
    @abc.abstractmethod
    async def get_water_information(self, dam_identifier: str, latitude: float, longitude: float) -> Dict[str, Any]:
        pass
