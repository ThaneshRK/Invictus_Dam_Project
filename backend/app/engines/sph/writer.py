import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, MultiPolygon
from app.engines.sph.particle import ParticleState
from app.engines.sph.spatialization import ParticleToGridInterpolator

class ResultWriter:
    """
    Converts SPH particle distributions into GIS-compatible raster grids.
    """
    def __init__(self, bounds: list, resolution: float, crs: str = "EPSG:4326"):
        self.bounds = bounds
        self.resolution = resolution
        self.crs = crs
        
        self.interpolator = ParticleToGridInterpolator(
            xmin=bounds[0], xmax=bounds[1], ymin=bounds[2], ymax=bounds[3], resolution=resolution
        )
        
        # Transform for the output grid (origin is top-left, y goes down)
        self.transform = rasterio.transform.from_origin(
            bounds[0], bounds[3], resolution, resolution
        )
        
    def process_frame(self, state: ParticleState, current_time: float):
        """
        Takes the current particle state and maps it to the 2D grid.
        Updates the maximum depth, velocity grids and arrival time.
        """
        fields = self.interpolator.interpolate_fields(state)
        self.interpolator.update_diagnostics(current_time, fields)

    def _generate_polygon(self, mask: np.ndarray) -> dict:
        """
        Generates a GeoJSON-like dict polygon from a boolean mask.
        """
        # Convert mask to uint8
        mask_uint8 = mask.astype(np.uint8)
        
        # Generate shapes
        shapes_gen = shapes(mask_uint8, mask=(mask_uint8 == 1), transform=self.transform)
        
        polygons = []
        for geom, val in shapes_gen:
            polygons.append(shape(geom))
            
        if not polygons:
            return None
            
        multi_poly = MultiPolygon(polygons)
        # Simplify geometry slightly to reduce size if it's very complex
        # multi_poly = multi_poly.simplify(self.resolution / 2.0)
        
        return multi_poly.__geo_interface__

    def get_final_results(self):
        """
        Returns the finalized grids formatted for the inundation_service.
        """
        inundation_mask = self.interpolator.get_inundation_mask(threshold=0.05)
        
        # Replace nodata with python None for JSON serialization
        max_depth = np.where(inundation_mask, self.interpolator.max_depth_grid, None)
        max_vel = np.where(inundation_mask, self.interpolator.max_vel_grid, None)
        arrival_time = np.where(inundation_mask, self.interpolator.arrival_time_grid, None)
        
        return {
            "max_depth_array": max_depth.tolist(),
            "max_velocity_array": max_vel.tolist(),
            "arrival_time_array": arrival_time.tolist(),
            "inundation_polygon": self._generate_polygon(inundation_mask),
            "bounds": self.bounds,
            "crs": self.crs,
            "transform": [
                self.transform.a, self.transform.b, self.transform.c,
                self.transform.d, self.transform.e, self.transform.f
            ]
        }
