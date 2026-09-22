import math
import os
from typing import Dict, Any, List
import geopandas as gpd
from datetime import datetime, timezone
import logging

from .base_provider import GovernmentDamProvider

logger = logging.getLogger(__name__)

class NRLDProvider(GovernmentDamProvider):
    """
    Real implementation for NRLD dam provider using provided Dam shapefile dataset.
    """
    
    _gdf = None

    def __init__(self):
        if NRLDProvider._gdf is None:
            try:
                # Path relative to the backend running dir (assuming backend is run from project root, or we find it)
                # Let's resolve the path robustly
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                dam_zip = os.path.join(base_dir, "datasets", "dam.zip")
                if not os.path.exists(dam_zip):
                    logger.warning(f"Dam dataset not found at {dam_zip}")
                    NRLDProvider._gdf = gpd.GeoDataFrame()
                else:
                    NRLDProvider._gdf = gpd.read_file(f"zip://{dam_zip}")
            except Exception as e:
                logger.error(f"Failed to load Dam dataset: {e}")
                NRLDProvider._gdf = gpd.GeoDataFrame()

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371.0 # Earth radius in kilometers
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2) * math.sin(dLat/2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dLon/2) * math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    async def find_nearby_dams(self, latitude: float, longitude: float, radius_km: float) -> List[Dict[str, Any]]:
        results = []
        if NRLDProvider._gdf is None or NRLDProvider._gdf.empty:
            return results

        # Iterate over rows. For performance, we could use spatial indexing (sindex),
        # but since we have Lat/Lon in columns, haversine is fine for ~5000 rows
        for idx, row in NRLDProvider._gdf.iterrows():
            try:
                dam_lat = float(row.get('dm_lat', 0))
                dam_lon = float(row.get('dm_long', 0))
                if dam_lat == 0 and dam_lon == 0:
                    continue

                dist = self._haversine_distance(latitude, longitude, dam_lat, dam_lon)
                if dist <= radius_km:
                    results.append({
                        "dam_name": str(row.get('dm_name', 'Unknown')),
                        "distance_km": dist,
                        "source_name": "Provided Dam Dataset",
                        "source_record_id": str(row.get('nrld_no', row.get('objectid', ''))),
                        "metadata": {
                            "state": str(row.get('state', '')),
                            "dam_type": str(row.get('dm_type', '')),
                            "year_completed": str(row.get('dm_cmp_yr', '')),
                            "seismic_zone": str(row.get('dm_ses_zon', ''))
                        }
                    })
            except Exception as e:
                logger.debug(f"Error processing dam row: {e}")
                
        # Sort by distance
        results.sort(key=lambda x: x["distance_km"])
        return results
        
    async def get_dam_details(self, dam_identifier: str) -> Dict[str, Any]:
        if NRLDProvider._gdf is None or NRLDProvider._gdf.empty:
            return {}
            
        # Find the dam by nrld_no or objectid
        match = NRLDProvider._gdf[(NRLDProvider._gdf['nrld_no'] == dam_identifier) | (NRLDProvider._gdf['objectid'].astype(str) == str(dam_identifier))]
        if not match.empty:
            row = match.iloc[0].to_dict()
            # Convert geometry to WKT or string so it's JSON serializable
            if 'geometry' in row:
                row['geometry'] = str(row['geometry'])
            
            return {
                "source_name": "Provided Dam Dataset",
                "source_url": "local://datasets/dam.zip",
                "source_record_id": dam_identifier,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "data": {k: str(v) for k, v in row.items()}
            }
        return {}
