import os
import rasterio
import numpy as np
from typing import Tuple

class Delft3DTerrainSampler:
    """Extracts terrain elevation from a DEM GeoTIFF for use in Delft3D-FM."""
    
    def __init__(self, workspace_path: str):
        self.output_dir = os.path.join(workspace_path, "terrain")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_xyz_bathymetry(
        self, 
        dem_path: str, 
        bounds: Tuple[float, float, float, float],
        filename: str = "bathymetry.xyz"
    ) -> str:
        """
        Extracts DEM pixels within the bounding box and saves them as a Delft3D .xyz sample file.
        
        Args:
            dem_path: Path to the GeoTIFF DEM
            bounds: (xmin, ymin, xmax, ymax) of the simulation domain
            filename: Output filename
            
        Returns:
            Absolute path to the generated .xyz file
        """
        output_path = os.path.join(self.output_dir, filename)
        xmin, ymin, xmax, ymax = bounds
        
        with rasterio.open(dem_path) as src:
            # We want to read only the window that covers our bounding box
            from rasterio.windows import from_bounds
            window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
            
            # Read the data and the window's transform
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            nodata = src.nodata
            
            # Get coordinates for all pixels in the window
            cols, rows = np.meshgrid(np.arange(data.shape[1]), np.arange(data.shape[0]))
            xs, ys = rasterio.transform.xy(win_transform, rows, cols)
            
            xs = np.array(xs).flatten()
            ys = np.array(ys).flatten()
            zs = data.flatten()
            
            # Filter out NoData values
            if nodata is not None:
                valid = zs != nodata
                xs = xs[valid]
                ys = ys[valid]
                zs = zs[valid]
                
            # Write to Delft3D .xyz format (space-separated x y z)
            # Delft3D-FM expects sample files to just be rows of: x y z
            with open(output_path, "w") as f:
                for x, y, z in zip(xs, ys, zs):
                    f.write(f"{x:.3f} {y:.3f} {z:.3f}\n")
                    
        return output_path
