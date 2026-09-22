import os
import glob
from typing import Dict, Any, List, Optional
import numpy as np

try:
    import xarray as xr
except ImportError:
    xr = None

class Delft3DResultParser:
    """Parses actual NetCDF/UGRID results from Delft3D-FM."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.output_dir = os.path.join(workspace_path, "output")
        
    def _find_map_file(self) -> Optional[str]:
        """Finds the map netCDF file produced by dflowfm."""
        if not os.path.exists(self.output_dir):
            return None
        nc_files = glob.glob(os.path.join(self.output_dir, "*_map.nc"))
        return nc_files[0] if nc_files else None

    def discover_variables(self, dataset: Any) -> Dict[str, str]:
        """Dynamically maps internal NetCDF variables to standard representations."""
        mapping = {}
        vars_available = list(dataset.variables.keys())
        
        # Look for water level
        for alias in ["mesh2d_s1", "s1", "waterlevel"]:
            if alias in vars_available:
                mapping["water_level"] = alias
                break
                
        # Look for water depth
        for alias in ["mesh2d_waterdepth", "waterdepth", "depth"]:
            if alias in vars_available:
                mapping["water_depth"] = alias
                break
                
        # Look for velocity X
        for alias in ["mesh2d_ucx", "ucx", "u1"]:
            if alias in vars_available:
                mapping["velocity_x"] = alias
                break

        # Look for velocity Y
        for alias in ["mesh2d_ucy", "ucy", "v1"]:
            if alias in vars_available:
                mapping["velocity_y"] = alias
                break
                
        # Time and coordinates usually have standard UGRID definitions
        mapping["time"] = "time" if "time" in vars_available else None
        
        # Identify nodes or faces for coordinates
        if "mesh2d_face_x" in vars_available and "mesh2d_face_y" in vars_available:
            mapping["x"] = "mesh2d_face_x"
            mapping["y"] = "mesh2d_face_y"
        elif "mesh2d_node_x" in vars_available and "mesh2d_node_y" in vars_available:
            mapping["x"] = "mesh2d_node_x"
            mapping["y"] = "mesh2d_node_y"
            
        return {k: v for k, v in mapping.items() if v is not None}

    def parse(self) -> Dict[str, Any]:
        """Loads the result metadata and summarizes it."""
        if xr is None:
            raise ImportError("xarray is not installed. Cannot parse Delft3D results.")
            
        map_file = self._find_map_file()
        if not map_file:
            raise FileNotFoundError(f"No Delft3D-FM map output (_map.nc) found in {self.output_dir}")
            
        try:
            ds = xr.open_dataset(map_file)
        except Exception as e:
            raise ValueError(f"Failed to open NetCDF file {map_file}: {e}")
            
        var_map = self.discover_variables(ds)
        
        # We don't read the whole array to memory for database blobs.
        # We extract statistics and bounds to store locally.
        
        result_metadata = {
            "source_file": os.path.relpath(map_file, self.workspace_path),
            "crs": ds.attrs.get("projected_coordinate_system", "Unknown"),
            "variables": var_map,
            "bounds": None,
            "max_water_depth": None
        }
        
        # Calculate bounding box
        if "x" in var_map and "y" in var_map:
            x_vals = ds[var_map["x"]].values
            y_vals = ds[var_map["y"]].values
            result_metadata["bounds"] = [
                float(np.min(x_vals)), float(np.max(x_vals)),
                float(np.min(y_vals)), float(np.max(y_vals))
            ]
            
        # Extract maximum depths
        if "water_depth" in var_map:
            depth_data = ds[var_map["water_depth"]].values
            # depth_data usually shape (time, faces)
            # Find the global maximum across all time steps
            max_d = np.nanmax(depth_data)
            result_metadata["max_water_depth"] = float(max_d)
            
        ds.close()

        # Generate GIS exports (GeoTIFFs and GeoJSON)
        gis_outputs = {}
        gis_stats = {}
        try:
            from app.services.delft3d.gis_export import Delft3DGISExporter
            exporter = Delft3DGISExporter(nc_path=map_file, output_dir=self.output_dir)
            gis_res = exporter.export_all()
            gis_outputs = gis_res.get("output_paths", {})
            gis_stats = gis_res.get("stats", {})
        except Exception as e:
            result_metadata["gis_export_error"] = str(e)

        result_metadata["outputs"] = gis_outputs
        result_metadata["stats"] = gis_stats
        return result_metadata
