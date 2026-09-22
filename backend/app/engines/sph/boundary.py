import numpy as np
import rasterio
from app.engines.sph.particle import ParticleState

class TerrainHandler:
    """
    Integrates DEM terrain for 2D SWE-SPH simulations.
    Provides terrain elevation (z_b) and gradient (∇z_b) at particle positions.
    """
    def __init__(self, dem_grid: np.ndarray, transform, nodata: float = None, crs=None):
        self.dem_grid = dem_grid
        self.transform = transform
        self.nodata = nodata
        self.crs = crs
        self.ny, self.nx = dem_grid.shape
        
        # Calculate cell size from transform
        self.cell_size_x = abs(transform[0])
        self.cell_size_y = abs(transform[4])
        
        # For simplicity in SWE, we assume uniform cell size in X and Y
        self.cell_size = (self.cell_size_x + self.cell_size_y) / 2.0

    @classmethod
    def from_geotiff(cls, filepath: str):
        with rasterio.open(filepath) as src:
            dem_grid = src.read(1)
            transform = src.transform
            nodata = src.nodata
            crs = src.crs
        return cls(dem_grid, transform, nodata, crs)

    def get_elevation_and_gradient(self, positions: np.ndarray):
        """
        Returns z_b and ∇z_b for an array of (x,y) positions using bilinear interpolation.
        """
        N = positions.shape[0]
        z = np.zeros(N)
        grad_z = np.zeros((N, 2))
        
        if self.dem_grid is None or self.dem_grid.size == 0:
            return z, grad_z

        # Convert positions to grid indices using inverse transform
        # transform: ~inv * (x, y) = (col, row)
        # However, for simplicity, if transform is standard:
        # col = (x - x0) / dx
        # row = (y - y0) / dy
        x0 = self.transform[2]
        y0 = self.transform[5]
        dx = self.transform[0]
        dy = self.transform[4] # usually negative
        
        x_idx = (positions[:, 0] - x0) / dx
        y_idx = (positions[:, 1] - y0) / dy
        
        # Valid mask
        valid = (x_idx >= 0) & (x_idx < self.nx - 1) & (y_idx >= 0) & (y_idx < self.ny - 1)
        
        x_valid = x_idx[valid]
        y_valid = y_idx[valid]
        
        x0_idx = np.floor(x_valid).astype(int)
        x1_idx = x0_idx + 1
        y0_idx = np.floor(y_valid).astype(int)
        y1_idx = y0_idx + 1
        
        dx_frac = x_valid - x0_idx
        dy_frac = y_valid - y0_idx
        
        # Grid values
        z00 = self.dem_grid[y0_idx, x0_idx]
        z10 = self.dem_grid[y0_idx, x1_idx]
        z01 = self.dem_grid[y1_idx, x0_idx]
        z11 = self.dem_grid[y1_idx, x1_idx]
        
        # Handle nodata if present (fallback to 0 or mean, simplest is keep as is and hope DEM is filled)
        if self.nodata is not None:
            nodata_mask = (z00 == self.nodata) | (z10 == self.nodata) | (z01 == self.nodata) | (z11 == self.nodata)
            # For nodata points, just set z to a high value so water flows away, or 0.
            # We'll use 0 for now if there's no better alternative, or skip interpolation.
            z00 = np.where(z00 == self.nodata, 0.0, z00)
            z10 = np.where(z10 == self.nodata, 0.0, z10)
            z01 = np.where(z01 == self.nodata, 0.0, z01)
            z11 = np.where(z11 == self.nodata, 0.0, z11)
        
        # Bilinear interpolation for Z
        z[valid] = (z00 * (1 - dx_frac) * (1 - dy_frac) +
                    z10 * dx_frac * (1 - dy_frac) +
                    z01 * (1 - dx_frac) * dy_frac +
                    z11 * dx_frac * dy_frac)
                    
        # Gradient ∇Z
        grad_z_x = (z10 - z00) * (1 - dy_frac) + (z11 - z01) * dy_frac
        grad_z_y = (z01 - z00) * (1 - dx_frac) + (z11 - z10) * dx_frac
        
        grad_z[valid, 0] = grad_z_x / dx
        grad_z[valid, 1] = grad_z_y / dy
        
        return z, grad_z


class DynamicBreach:
    def __init__(self, xmin, xmax, ymin, ymax, failure_time: float, formation_time: float, final_width: float):
        self.xmin_base = xmin
        self.xmax_base = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.failure_time = failure_time
        self.formation_time = formation_time
        self.final_width = final_width
        
        self.center_x = (xmin + xmax) / 2.0
        
    def get_current_bounds(self, time: float):
        """Returns the active boundary box considering the breach opening."""
        if time < self.failure_time:
            # Closed
            return [{"xmin": self.xmin_base, "xmax": self.xmax_base, "ymin": self.ymin, "ymax": self.ymax}]
            
        elif time > self.failure_time + self.formation_time:
            # Fully open
            w = self.final_width / 2.0
            return [
                {"xmin": self.xmin_base, "xmax": self.center_x - w, "ymin": self.ymin, "ymax": self.ymax},
                {"xmin": self.center_x + w, "xmax": self.xmax_base, "ymin": self.ymin, "ymax": self.ymax}
            ]
        else:
            # Progressively opening
            progress = (time - self.failure_time) / self.formation_time
            w = (self.final_width / 2.0) * progress
            return [
                {"xmin": self.xmin_base, "xmax": self.center_x - w, "ymin": self.ymin, "ymax": self.ymax},
                {"xmin": self.center_x + w, "xmax": self.xmax_base, "ymin": self.ymin, "ymax": self.ymax}
            ]

class BoundaryHandler:
    """
    Enforces rigid boundaries, dynamic breaches, and blockages.
    """
    def __init__(self, bounds: list, restitution: float = 0.0):
        # bounds: [xmin, xmax, ymin, ymax]
        self.bounds = bounds
        self.restitution = restitution
        self.blockages = [] 
        self.breaches = []

    def add_blockage(self, xmin: float, xmax: float, ymin: float, ymax: float):
        self.blockages.append({
            "xmin": xmin,
            "xmax": xmax,
            "ymin": ymin,
            "ymax": ymax
        })
        
    def add_dynamic_breach(self, breach: DynamicBreach):
        self.breaches.append(breach)

    def enforce_boundaries(self, state: ParticleState, current_time: float = 0.0):
        fluid_idx = state.get_fluid_indices()
        if len(fluid_idx) == 0:
            return
            
        pos = state.pos[fluid_idx]
        vel = state.vel[fluid_idx]
        
        # Domain boundaries
        if self.bounds:
            xmin, xmax, ymin, ymax = self.bounds
            
            hit_left = pos[:, 0] < xmin
            pos[hit_left, 0] = xmin
            vel[hit_left, 0] *= -self.restitution
            
            hit_right = pos[:, 0] > xmax
            pos[hit_right, 0] = xmax
            vel[hit_right, 0] *= -self.restitution
            
            hit_bottom = pos[:, 1] < ymin
            pos[hit_bottom, 1] = ymin
            vel[hit_bottom, 1] *= -self.restitution
            
            hit_top = pos[:, 1] > ymax
            pos[hit_top, 1] = ymax
            vel[hit_top, 1] *= -self.restitution
        
        # Collect active rectangular boundaries (blockages + active breach parts)
        active_rects = list(self.blockages)
        for b in self.breaches:
            active_rects.extend(b.get_current_bounds(current_time))
        
        # AABB Collisions
        for block in active_rects:
            b_xmin, b_xmax, b_ymin, b_ymax = block["xmin"], block["xmax"], block["ymin"], block["ymax"]
            if b_xmax <= b_xmin or b_ymax <= b_ymin:
                continue
                
            in_x = (pos[:, 0] > b_xmin) & (pos[:, 0] < b_xmax)
            in_y = (pos[:, 1] > b_ymin) & (pos[:, 1] < b_ymax)
            in_block = in_x & in_y
            
            if np.any(in_block):
                dx1 = pos[:, 0] - b_xmin
                dx2 = b_xmax - pos[:, 0]
                dy1 = pos[:, 1] - b_ymin
                dy2 = b_ymax - pos[:, 1]
                
                min_d = np.minimum(np.minimum(dx1, dx2), np.minimum(dy1, dy2))
                
                push_left = in_block & (dx1 == min_d)
                pos[push_left, 0] = b_xmin
                vel[push_left, 0] *= -self.restitution
                
                push_right = in_block & (dx2 == min_d)
                pos[push_right, 0] = b_xmax
                vel[push_right, 0] *= -self.restitution
                
                push_bottom = in_block & (dy1 == min_d)
                pos[push_bottom, 1] = b_ymin
                vel[push_bottom, 1] *= -self.restitution
                
                push_top = in_block & (dy2 == min_d)
                pos[push_top, 1] = b_ymax
                vel[push_top, 1] *= -self.restitution

        state.pos[fluid_idx] = pos
        state.vel[fluid_idx] = vel
