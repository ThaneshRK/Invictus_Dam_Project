import os
import logging
from typing import Dict, Any, Tuple
import numpy as np
import rasterio
from app.core.simulation_context import SimulationInputContext
from app.engines.sph.boundary import TerrainHandler, DynamicBreach
from app.engines.utils import resolve_dataset_path
from geoalchemy2.shape import to_shape
import shapely.geometry

logger = logging.getLogger(__name__)

class SPHInputBuilder:
    """
    Translates the validated SimulationInputContext into SPH engine configuration and geometries.
    """
    def __init__(self, context: SimulationInputContext):
        self.context = context
        self.params = self.context.scenario.parameters or {}
        
    def build(self) -> Dict[str, Any]:
        """
        Returns a dictionary containing the fully realized engine inputs.
        """
        # 1. Bounds & Terrain
        domain_bounds = [0.0, 100.0, 0.0, 100.0]
        terrain = None
        dem_path = None
        
        dem_path = resolve_dataset_path(self.context.dem)

        if dem_path and os.path.exists(dem_path):
            try:
                terrain = TerrainHandler.from_geotiff(dem_path)
                with rasterio.open(dem_path) as src:
                    domain_bounds = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
            except Exception as err:
                logger.warning(f"Could not parse DEM geotiff {dem_path}: {err}")
        
        if terrain is None:
            if hasattr(self.context, 'study_area') and self.context.study_area:
                study_geom = to_shape(self.context.study_area)
                b = study_geom.bounds
                domain_bounds = [b[0], b[2], b[1], b[3]]
            # Flat synthetic fallback terrain (50x50) spanning the domain,
            # so the solver degrades gracefully instead of crashing.
            logger.warning(
                "SPH builder: no usable DEM provided; falling back to flat synthetic terrain "
                f"over bounds {domain_bounds}. Results are schematic only."
            )
            fallback_grid = np.zeros((50, 50), dtype=np.float64)
            fallback_transform = rasterio.transform.from_bounds(
                domain_bounds[0], domain_bounds[2], domain_bounds[1], domain_bounds[3], 50, 50
            )
            terrain = TerrainHandler(fallback_grid, fallback_transform)

        # 2. Dam Geometry
        dam_geom = to_shape(self.context.dam.geometry)
        dam_x, dam_y = dam_geom.x, dam_geom.y
        
        # 3. Reservoir Geometry (Initial water polygon)
        reservoir_geom = to_shape(self.context.reservoir.geometry)
        res_minx, res_miny, res_maxx, res_maxy = reservoir_geom.bounds
        water_poly = [res_minx, res_maxx, res_miny, res_maxy]
        
        st = self.context.scenario.scenario_type
        scen_type = st.value if hasattr(st, 'value') else str(st)
        
        # 4. River Blockage
        blockages = []
        if scen_type == "RIVER_BLOCKAGE":
            # Extract blockage from river bounding box or intersection point
            river_geom = to_shape(self.context.river.geometry)
            r_minx, r_miny, r_maxx, r_maxy = river_geom.bounds
            blockages.append({
                "xmin": r_minx, "xmax": r_maxx,
                "ymin": r_miny, "ymax": r_maxy
            })
            
        # 5. Dam representation & breach parameters
        #
        # The prototype represents the dam as a vertical AABB wall (DynamicBreach)
        # centred on the dam location:
        #   DAM_BREAK      -> wall fails at failure_time and erodes to breach_width
        #   WATER_RELEASE  -> wall stays, spillway gates open a narrow release_width
        #   RIVER_BLOCKAGE -> wall never fails (failure_time = inf); the downstream
        #                     landslide blockage is what fails (handled by the engine)
        breach = None
        breach_width = self.params.get("breach_width", 20.0)
        if scen_type == "DAM_BREAK":
            breach = DynamicBreach(
                xmin=dam_x - breach_width/2.0, xmax=dam_x + breach_width/2.0,
                ymin=dam_y - 10.0, ymax=dam_y + 10.0, # Approximate breach bounding along dam
                failure_time=self.params.get("failure_time", 2.0),
                formation_time=self.params.get("formation_time", 5.0),
                final_width=breach_width
            )
        elif scen_type == "WATER_RELEASE":
            release_width = self.params.get("release_width", max(5.0, 0.1 * breach_width))
            breach = DynamicBreach(
                xmin=dam_x - release_width/2.0, xmax=dam_x + release_width/2.0,
                ymin=dam_y - 10.0, ymax=dam_y + 10.0,
                failure_time=self.params.get("failure_time", 1.0),
                formation_time=self.params.get("formation_time", 2.0),
                final_width=release_width
            )
        elif scen_type == "RIVER_BLOCKAGE":
            breach = DynamicBreach(
                xmin=dam_x - breach_width/2.0, xmax=dam_x + breach_width/2.0,
                ymin=dam_y - 10.0, ymax=dam_y + 10.0,
                failure_time=float("inf"),  # dam stays intact; landslide blockage fails instead
                formation_time=1.0,
                final_width=breach_width
            )

        # 6. Hydrology
        initial_water_level = self.params.get("initial_water_level", 20.0)
        discharge_curve = None
        if self.context.hydrology and "file_path" in self.context.hydrology.metadata:
            # We would parse the CSV hydrograph here
            pass

        return {
            "domain_bounds": domain_bounds,
            "terrain": terrain,
            "water_poly": water_poly,
            "initial_water_level": initial_water_level,
            "blockages": blockages,
            "breach": breach,
            "duration_s": self.context.scenario.simulation_duration * 3600,
            "duration_cap_s": float(self.params.get("duration_cap_s", 5.0)),
            "scenario_type": scen_type,
            "particle_spacing": self.params.get("particle_spacing", 1.0),
            "smoothing_length": self.params.get("smoothing_length", 2.0)
        }
