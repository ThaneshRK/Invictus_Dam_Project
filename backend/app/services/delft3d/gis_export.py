"""
Delft3D GIS Exporter.

Converts Delft3D-FM UGRID NetCDF output (*_map.nc) into standard GIS deliverables:
- Max depth GeoTIFF (max_depth.tif)
- Max velocity magnitude GeoTIFF (max_velocity.tif)
- Arrival time GeoTIFF (arrival_time.tif)
- Inundation extent GeoJSON (inundation_extent.geojson)
"""

import os
import json
import numpy as np
import xarray as xr
from typing import Dict, Any, Optional, Tuple
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import shapes
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import unary_union

class Delft3DGISExporter:
    """Exports Delft3D NetCDF results to GeoTIFF and GeoJSON format."""

    def __init__(self, nc_path: str, output_dir: str, grid_resolution_m: float = 10.0, crs_epsg: int = 4326):
        self.nc_path = nc_path
        self.output_dir = output_dir
        self.grid_resolution_m = grid_resolution_m
        self.crs_epsg = crs_epsg
        os.makedirs(self.output_dir, exist_ok=True)

    def export_all(self, depth_threshold_m: float = 0.05) -> Dict[str, Any]:
        """Runs full GIS export workflow and returns paths + stats."""
        if not os.path.exists(self.nc_path):
            raise FileNotFoundError(f"NetCDF map file not found: {self.nc_path}")

        ds = xr.open_dataset(self.nc_path)

        # Identify coordinate variables
        x_var = "mesh2d_face_x" if "mesh2d_face_x" in ds else ("mesh2d_node_x" if "mesh2d_node_x" in ds else "x")
        y_var = "mesh2d_face_y" if "mesh2d_face_y" in ds else ("mesh2d_node_y" if "mesh2d_node_y" in ds else "y")

        x_pts = ds[x_var].values
        y_pts = ds[y_var].values

        min_x, max_x = float(np.min(x_pts)), float(np.max(x_pts))
        min_y, max_y = float(np.min(y_pts)), float(np.max(y_pts))

        # Build regular raster grid grid dimensions
        # Estimate pixel count based on extent
        extent_x = max_x - min_x
        extent_y = max_y - min_y

        # If CRS is degree based (EPSG:4326), convert res to degrees approx
        if self.crs_epsg == 4326 and extent_x < 10.0:  # degrees
            res_deg = self.grid_resolution_m / 111_000.0
            nx = max(10, int(np.ceil(extent_x / res_deg)))
            ny = max(10, int(np.ceil(extent_y / res_deg)))
        else:
            nx = max(10, int(np.ceil(extent_x / self.grid_resolution_m)))
            ny = max(10, int(np.ceil(extent_y / self.grid_resolution_m)))

        grid_x = np.linspace(min_x, max_x, nx)
        grid_y = np.linspace(max_y, min_y, ny)  # top-down for raster
        gx, gy = np.meshgrid(grid_x, grid_y)

        transform = from_bounds(min_x, min_y, max_x, max_y, nx, ny)

        # 1. Process Water Depth (max across time)
        depth_var = "mesh2d_waterdepth" if "mesh2d_waterdepth" in ds else ("s1" if "s1" in ds else None)
        if depth_var and depth_var in ds:
            depth_data = ds[depth_var].values  # shape (time, faces) or (faces,)
            if depth_data.ndim == 2:
                max_depth_pts = np.nanmax(depth_data, axis=0)
            else:
                max_depth_pts = depth_data
        else:
            max_depth_pts = np.zeros_like(x_pts)

        # Interpolate max depth onto regular grid
        grid_max_depth = griddata((x_pts, y_pts), max_depth_pts, (gx, gy), method='linear', fill_value=0.0)
        grid_max_depth = np.maximum(0.0, np.nan_to_num(grid_max_depth, nan=0.0))

        max_depth_tif = os.path.join(self.output_dir, "max_depth.tif")
        self._write_geotiff(max_depth_tif, grid_max_depth.astype(np.float32), transform, nx, ny)

        # 2. Process Velocity Magnitude (max across time)
        ucx_var = "mesh2d_ucx" if "mesh2d_ucx" in ds else ("ucx" if "ucx" in ds else None)
        ucy_var = "mesh2d_ucy" if "mesh2d_ucy" in ds else ("ucy" if "ucy" in ds else None)

        if ucx_var and ucy_var and ucx_var in ds and ucy_var in ds:
            u = ds[ucx_var].values
            v = ds[ucy_var].values
            vel_pts = np.sqrt(u**2 + v**2)
            if vel_pts.ndim == 2:
                max_vel_pts = np.nanmax(vel_pts, axis=0)
            else:
                max_vel_pts = vel_pts
        else:
            max_vel_pts = np.zeros_like(x_pts)

        grid_max_vel = griddata((x_pts, y_pts), max_vel_pts, (gx, gy), method='linear', fill_value=0.0)
        grid_max_vel = np.maximum(0.0, np.nan_to_num(grid_max_vel, nan=0.0))

        max_vel_tif = os.path.join(self.output_dir, "max_velocity.tif")
        self._write_geotiff(max_vel_tif, grid_max_vel.astype(np.float32), transform, nx, ny)

        # 3. Process Arrival Time (hours after start)
        arrival_grid = np.full((ny, nx), fill_value=-1.0, dtype=np.float32)
        if depth_var and depth_var in ds and ds[depth_var].ndim == 2:
            time_vals = ds["time"].values if "time" in ds else np.arange(ds[depth_var].shape[0])
            # Convert time_vals to hours from start
            if np.issubdtype(time_vals.dtype, np.datetime64):
                t_hours = (time_vals - time_vals[0]).astype('timedelta64[s]').astype(float) / 3600.0
            else:
                t_hours = (time_vals - time_vals[0]) / 3600.0

            # Find first time step where depth > depth_threshold_m for each point
            depth_series = ds[depth_var].values  # (time, faces)
            arrival_pts = np.full(x_pts.shape, fill_value=-1.0)
            for t_idx, t_h in enumerate(t_hours):
                wet_mask = (depth_series[t_idx] >= depth_threshold_m) & (arrival_pts < 0)
                arrival_pts[wet_mask] = t_h

            grid_arrival = griddata((x_pts, y_pts), arrival_pts, (gx, gy), method='nearest', fill_value=-1.0)
            arrival_grid = np.nan_to_num(grid_arrival, nan=-1.0).astype(np.float32)

        arrival_tif = os.path.join(self.output_dir, "arrival_time.tif")
        self._write_geotiff(arrival_tif, arrival_grid, transform, nx, ny)

        # 4. Generate Inundation Extent GeoJSON
        geojson_path = os.path.join(self.output_dir, "inundation_extent.geojson")
        mask = (grid_max_depth >= depth_threshold_m).astype(np.uint8)

        polygons = []
        for geom, val in shapes(mask, transform=transform):
            if val == 1:
                polygons.append(shape(geom))

        if polygons:
            merged_poly = unary_union(polygons)
            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "threshold_m": depth_threshold_m,
                            "max_depth_m": float(np.max(grid_max_depth)),
                            "mean_depth_m": float(np.mean(grid_max_depth[grid_max_depth >= depth_threshold_m])) if np.any(grid_max_depth >= depth_threshold_m) else 0.0,
                        },
                        "geometry": mapping(merged_poly)
                    }
                ]
            }
        else:
            geojson_data = {"type": "FeatureCollection", "features": []}

        with open(geojson_path, "w") as f:
            json.dump(geojson_data, f, indent=2)

        # Compute summary stats
        inundated_cells = np.sum(grid_max_depth >= depth_threshold_m)
        cell_area_m2 = (extent_x / nx) * (extent_y / ny)
        if self.crs_epsg == 4326 and extent_x < 10.0:
            # Approx 1 deg ~ 111km
            cell_area_km2 = cell_area_m2 * (111.0 ** 2)
        else:
            cell_area_km2 = cell_area_m2 / 1_000_000.0

        inundated_area_km2 = float(inundated_cells * cell_area_km2)
        max_depth_m = float(np.max(grid_max_depth))
        mean_depth_m = float(np.mean(grid_max_depth[grid_max_depth >= depth_threshold_m])) if inundated_cells > 0 else 0.0

        ds.close()

        return {
            "stats": {
                "max_depth_m": max_depth_m,
                "mean_depth_m": mean_depth_m,
                "max_velocity_ms": float(np.max(grid_max_vel)),
                "inundated_area_km2": inundated_area_km2
            },
            "output_paths": {
                "max_depth_geotiff": max_depth_tif,
                "max_velocity_geotiff": max_vel_tif,
                "arrival_time_geotiff": arrival_tif,
                "inundation_extent_geojson": geojson_path
            }
        }

    def _write_geotiff(self, filepath: str, data: np.ndarray, transform: Any, nx: int, ny: int):
        """Helper to write a 2D float array to single-band GeoTIFF."""
        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=ny,
            width=nx,
            count=1,
            dtype=data.dtype,
            crs=f"EPSG:{self.crs_epsg}",
            transform=transform,
            nodata=-1.0 if "arrival" in filepath else 0.0
        ) as dst:
            dst.write(data, 1)
