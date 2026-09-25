import asyncio
import json
import pyproj
from typing import Tuple, Dict, Any, List
import geopandas as gpd

from app.services.government_data.providers_impl import BhuvanDEMProvider, NWICProvider, BBMBProvider

class DataAcquisitionManager:
    def __init__(self):
        self.dem_providers = [BhuvanDEMProvider()]
        self.hydro_providers = [BBMBProvider(), NWICProvider()]
        
        # Load local base datasets
        self.dams_gdf = gpd.read_file('zip://datasets/dam.zip')
        self.res_gdf = gpd.read_file('zip://datasets/Reservoir.zip')
        self.riv_gdf = gpd.read_file('zip://datasets/Rivers.zip')
        
    def _find_dam(self, dam_name: str) -> gpd.GeoDataFrame:
        return self.dams_gdf[self.dams_gdf['dm_name'].str.contains(dam_name, na=False, case=False)]
        
    def _find_reservoir(self, dam: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # Spatial match or string match
        if dam.empty: return gpd.GeoDataFrame()
        dam_name = dam.iloc[0]['dm_name'].replace(" Dam", "")
        # Very simplified string fallback
        return self.res_gdf[self.res_gdf['wbname'].str.contains(dam_name, na=False, case=False)]
        
    def _find_river(self, dam: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if dam.empty: return gpd.GeoDataFrame()
        rivcode = dam.iloc[0].get('rivcode', '')
        if not rivcode: return gpd.GeoDataFrame()
        return self.riv_gdf[self.riv_gdf['rivname'].str.contains(rivcode, na=False, case=False)]

    def _compute_simulation_domain(self, dam: gpd.GeoDataFrame, res: gpd.GeoDataFrame, riv: gpd.GeoDataFrame) -> Tuple[float, float, float, float]:
        # Compute bounding box in projected CRS, then convert to WGS84
        minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        for df in [dam, res]:
            if not df.empty:
                b = df.geometry.total_bounds
                minx, miny = min(minx, b[0]), min(miny, b[1])
                maxx, maxy = max(maxx, b[2]), max(maxy, b[3])
                
        # For river, only take up to 30km downstream from dam to avoid taking entire river length
        # Simplified: Just add a buffer around the dam/reservoir
        if minx != float('inf'):
            minx -= 10000 # 10 km buffer
            miny -= 10000
            maxx += 10000
            maxy += 10000
            
        # Transform to WGS84 (assuming EPSG 4326)
        source_crs = dam.crs
        if source_crs is None:
            source_crs = "EPSG:32643" # Fallback
            
        transformer = pyproj.Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        lon_min, lat_min = transformer.transform(minx, miny)
        lon_max, lat_max = transformer.transform(maxx, maxy)
        
        return (lon_min, lat_min, lon_max, lat_max)

    def _determine_metric_crs(self, lon: float) -> str:
        # Determine UTM zone from longitude
        zone = int((lon + 180) / 6) + 1
        return f"EPSG:326{zone}" if lon > 0 else f"EPSG:327{zone}" # simplified for N/S

    async def run_acquisition_workflow(self, dam_name: str) -> Dict[str, Any]:
        report = {
            "dam": dam_name,
            "status": "READY",
            "datasets": [],
            "issues": []
        }
        
        # 1. Resolve features
        dam_df = self._find_dam(dam_name)
        if dam_df.empty:
            report["status"] = "BLOCKED_MISSING_DAM"
            report["issues"].append(f"Dam {dam_name} not found in inventory.")
            return report
            
        res_df = self._find_reservoir(dam_df)
        riv_df = self._find_river(dam_df)
        
        dam_lon, dam_lat = dam_df.geometry.x.iloc[0] if dam_df.geometry.type.iloc[0] == 'Point' else 0, 0
        if dam_lon == 0:
            dam_lon, dam_lat = dam_df.iloc[0].get('dm_long', 0), dam_df.iloc[0].get('dm_lat', 0)
        
        # 2. Determine simulation domain & CRS
        bbox = self._compute_simulation_domain(dam_df, res_df, riv_df)
        target_crs = self._determine_metric_crs((bbox[0] + bbox[2]) / 2)
        
        report["simulation_domain_wgs84"] = bbox
        report["target_crs"] = target_crs
        
        # 3. DEM Acquisition
        dem_provider = self.dem_providers[0]
        try:
            dem = await dem_provider.acquire_dem(bbox, target_crs, "datasets/dem/")
            report["datasets"].append(dem.dict())
        except Exception as e:
            report["status"] = "BLOCKED_NEEDS_SOURCE_ACCESS"
            report["issues"].append(str(e))
            report["datasets"].append({
                "type": "DEM",
                "provider": dem_provider.get_provider_name(),
                "status": "FAILED",
                "reason": str(e)
            })
            
        # 4. Hydrology Acquisition (Initial Water Level for DAM_BREAK)
        hydro_success = False
        for hp in self.hydro_providers:
            try:
                hydro = await hp.get_reservoir_level(
                    res_df.iloc[0]['wbname'] if not res_df.empty else "",
                    dam_df.iloc[0]['dm_name']
                )
                if hydro:
                    report["datasets"].append(hydro.dict())
                    hydro_success = True
                    break
            except Exception as e:
                report["issues"].append(str(e))
                report["datasets"].append({
                    "type": "Hydrology",
                    "provider": hp.get_provider_name(),
                    "status": "FAILED",
                    "reason": str(e)
                })
                
        if not hydro_success and report["status"] == "READY":
            report["status"] = "BLOCKED_NEEDS_SOURCE_ACCESS"
            
        return report

async def main():
    manager = DataAcquisitionManager()
    
    print("=== BHAKRA FIRST TEST ===")
    bhakra_report = await manager.run_acquisition_workflow("Bhakra")
    print(json.dumps(bhakra_report, indent=2))
    
    print("\n=== HIRAKUD GENERALIZATION TEST ===")
    hirakud_report = await manager.run_acquisition_workflow("Hirakud")
    print(json.dumps(hirakud_report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
