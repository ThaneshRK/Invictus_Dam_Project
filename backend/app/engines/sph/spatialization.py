import numpy as np
from scipy.stats import binned_statistic_2d
from app.engines.sph.particle import ParticleState

class ParticleToGridInterpolator:
    """
    Interpolates SPH particle properties onto a regular Cartesian grid.
    Supports: water depth, water surface elevation, velocities, arrival time.
    """
    def __init__(self, xmin: float, xmax: float, ymin: float, ymax: float, resolution: float, nodata: float = -9999.0):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.resolution = resolution
        self.nodata = nodata
        
        self.nx = int(np.ceil((xmax - xmin) / resolution))
        self.ny = int(np.ceil((ymax - ymin) / resolution))
        
        self.xbins = np.linspace(xmin, xmin + self.nx * resolution, self.nx + 1)
        self.ybins = np.linspace(ymin, ymin + self.ny * resolution, self.ny + 1)
        
        self.arrival_time_grid = np.full((self.ny, self.nx), -1.0, dtype=np.float64)
        self.max_depth_grid = np.zeros((self.ny, self.nx), dtype=np.float64)
        self.max_vel_grid = np.zeros((self.ny, self.nx), dtype=np.float64)

    def interpolate_fields(self, state: ParticleState) -> dict:
        """
        Interpolates current particle state to grid using cell-averaging.
        Returns a dictionary of interpolated grids.
        """
        fluid_idx = state.get_fluid_indices()
        
        if len(fluid_idx) == 0:
            empty = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
            return {
                "depth": empty.copy(),
                "surface_elevation": empty.copy(),
                "u_vel": empty.copy(),
                "v_vel": empty.copy(),
                "vel_mag": empty.copy()
            }
            
        pos = state.pos[fluid_idx]
        x = pos[:, 0]
        y = pos[:, 1]
        
        u = state.vel[fluid_idx, 0]
        v = state.vel[fluid_idx, 1]
        vel_mag = np.linalg.norm(state.vel[fluid_idx], axis=1)
        
        # Spatial Binning
        if state.dim == 3:
            z = state.pos[fluid_idx, 2]
            max_z, _, _, _ = binned_statistic_2d(y, x, z, statistic='max', bins=[self.ybins, self.xbins])
            mean_zb, _, _, _ = binned_statistic_2d(y, x, state.z_b[fluid_idx], statistic='mean', bins=[self.ybins, self.xbins])
            
            valid_mask = ~np.isnan(max_z)
            avg_h = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
            avg_h[valid_mask] = max_z[valid_mask] - mean_zb[valid_mask]
            
            avg_eta = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
            avg_eta[valid_mask] = max_z[valid_mask]
            
            count, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins])
            # Ensure valid_mask aligns with count > 0 for velocity
        else:
            h_depth = state.h_depth[fluid_idx]
            z_b = state.z_b[fluid_idx]
            eta = h_depth + z_b
            
            count, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins])
            valid_mask = count > 0
            
            sum_h, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins], weights=h_depth)
            avg_h = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
            avg_h[valid_mask] = sum_h[valid_mask] / count[valid_mask]
            
            sum_eta, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins], weights=eta)
            avg_eta = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
            avg_eta[valid_mask] = sum_eta[valid_mask] / count[valid_mask]
        
        sum_u, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins], weights=u)
        avg_u = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
        avg_u[valid_mask] = sum_u[valid_mask] / count[valid_mask]
        
        sum_v, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins], weights=v)
        avg_v = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
        avg_v[valid_mask] = sum_v[valid_mask] / count[valid_mask]
        
        sum_mag, _, _ = np.histogram2d(y, x, bins=[self.ybins, self.xbins], weights=vel_mag)
        avg_mag = np.full((self.ny, self.nx), self.nodata, dtype=np.float64)
        avg_mag[valid_mask] = sum_mag[valid_mask] / count[valid_mask]
        
        return {
            "depth": avg_h,
            "surface_elevation": avg_eta,
            "u_vel": avg_u,
            "v_vel": avg_v,
            "vel_mag": avg_mag
        }

    def update_diagnostics(self, current_time: float, current_fields: dict, inundation_threshold: float = 0.05):
        """
        Updates cumulative maximum grids and arrival times.
        """
        depth = current_fields["depth"]
        vel_mag = current_fields["vel_mag"]
        
        valid_cells = depth != self.nodata
        
        # Update max depth
        self.max_depth_grid[valid_cells] = np.maximum(
            self.max_depth_grid[valid_cells], 
            depth[valid_cells]
        )
        
        # Update max velocity
        self.max_vel_grid[valid_cells] = np.maximum(
            self.max_vel_grid[valid_cells], 
            vel_mag[valid_cells]
        )
        
        # Update arrival time
        newly_flooded = (depth >= inundation_threshold) & (self.arrival_time_grid == -1.0) & valid_cells
        self.arrival_time_grid[newly_flooded] = current_time

    def get_inundation_mask(self, threshold: float = 0.05) -> np.ndarray:
        return self.max_depth_grid >= threshold
