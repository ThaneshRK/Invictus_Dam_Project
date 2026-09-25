import uuid
import numpy as np
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.result import SimulationResult
from app.models.scenario import Scenario

class InundationService:
    """
    Service for post-processing engine outputs into standardized inundation grids and stats.
    """
    @staticmethod
    def process_engine_output(engine_results: Dict[str, Any], threshold_m: float = 0.10) -> Dict[str, Any]:
        """
        Takes engine results, processes array or file-path based GIS stats and outputs.
        """
        # If engine already computed stats and outputs (e.g. Delft3D GIS exporter)
        if "stats" in engine_results and "outputs" in engine_results:
            return {
                "stats": engine_results["stats"],
                "output_paths": engine_results["outputs"]
            }

        if "max_depth_array" not in engine_results or engine_results["max_depth_array"] is None:
            return {"error": "Missing depth output from engine"}

        depth_grid = np.nan_to_num(np.array(engine_results["max_depth_array"], dtype=np.float64), nan=0.0)

        # Apply inundation threshold
        inundated_mask = depth_grid > threshold_m

        # Calculate Statistics
        if np.any(inundated_mask):
            max_depth = float(np.max(depth_grid[inundated_mask]))
            mean_depth = float(np.mean(depth_grid[inundated_mask]))
            inundated_area_km2 = float(np.sum(inundated_mask) * 4 / 1_000_000)
        else:
            max_depth = 0.0
            mean_depth = 0.0
            inundated_area_km2 = 0.0

        max_velocity = float(engine_results.get("max_velocity_ms", 0.0))
        
        output_paths = {
            "inundation_extent": engine_results.get("inundation_extent_path", "/data/outputs/extent.tif"),
            "water_depth": engine_results.get("water_depth_path", "/data/outputs/depth.tif"),
            "velocity_magnitude": engine_results.get("velocity_magnitude_path", "/data/outputs/velocity.tif"),
            "arrival_time": engine_results.get("arrival_time_path", "/data/outputs/arrival.tif"),
            "polygons": engine_results.get("polygons_path", "/data/outputs/polygons.geojson")
        }
        if "inundation_polygon" in engine_results and engine_results["inundation_polygon"]:
            output_paths["inundation_polygon"] = engine_results["inundation_polygon"]

        return {
            "stats": {
                "max_depth_m": max_depth,
                "mean_depth_m": mean_depth,
                "max_velocity_ms": max_velocity,
                "inundated_area_km2": inundated_area_km2
            },
            "output_paths": output_paths
        }

    @staticmethod
    async def create_result_record(db: AsyncSession, project_id: uuid.UUID, scenario_id: uuid.UUID, engine_name: str, crs: str, processed_results: Dict[str, Any]) -> SimulationResult:
        stats = processed_results.get("stats", {})
        
        result = SimulationResult(
            project_id=project_id,
            scenario_id=scenario_id,
            engine_used=engine_name,
            crs=crs,
            outputs=processed_results.get("output_paths", {}),
            inundated_area_km2=stats.get("inundated_area_km2"),
            max_depth_m=stats.get("max_depth_m"),
            mean_depth_m=stats.get("mean_depth_m"),
            max_velocity_ms=stats.get("max_velocity_ms")
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        return result
