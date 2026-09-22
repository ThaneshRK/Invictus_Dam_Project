from typing import Dict, Any, List
from .base_provider import PopulationProvider
from datetime import datetime, timezone

class MockPopulationProvider(PopulationProvider):
    """
    Mock implementation for Population Provider.
    In a real implementation, this would query a Census API or PostGIS spatial intersection on census polygons.
    """
    
    async def get_population(self, latitude: float, longitude: float, radii_km: List[float]) -> Dict[str, Any]:
        # For Mettur dam coordinates (~11.8, 77.8), we'll return some realistic static estimations
        # Base population density approx 450 people per sq km
        density = 450
        
        results = {}
        for r in radii_km:
            area = 3.14159 * (r ** 2)
            pop = int(area * density)
            results[f"population_{int(r)}km"] = pop
            
        return {
            "source_name": "Census of India 2011 (Estimated Projection)",
            "reference_year": 2011,
            "methodology": "Area-proportional density estimation from district aggregates",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "data": results
        }

    async def get_population_by_bbox(self, bbox: tuple[float, float, float, float]) -> Dict[str, Any]:
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Simple estimation based on bounding box area for mock
        # Assuming ~111km per degree
        width_km = abs(max_lon - min_lon) * 111
        height_km = abs(max_lat - min_lat) * 111
        area_sq_km = width_km * height_km
        
        density = 450
        pop = int(area_sq_km * density)
        
        return {
            "source_name": "Census of India 2011 (Estimated Projection)",
            "reference_year": 2011,
            "methodology": "Area-proportional density estimation by bounding box",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "total_population": pop
        }
