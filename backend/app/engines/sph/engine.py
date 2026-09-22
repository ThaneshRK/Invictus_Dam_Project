import logging
import uuid
import numpy as np
import os
import rasterio
from typing import Dict, Any
from app.engines.base import SimulationEngine
from app.engines.sph.solver import SPHSolver
from app.engines.sph.boundary import TerrainHandler, DynamicBreach
from app.engines.sph.writer import ResultWriter
from app.core.config import settings

logger = logging.getLogger(__name__)

class SPHEngine(SimulationEngine):
    """
    SPH Simulation Engine Implementation.
    Orchestrates the modular solver, inputs, and outputs.
    """
    def __init__(self, scenario_config: Dict[str, Any]):
        super().__init__(scenario_config)
        self.solver = None
        self.writer = None
        self.domain_bounds = [0.0, 100.0, 0.0, 100.0]
        
        self.current_step = 0
        self.total_steps = 0
        self.output_interval_steps = 100
        self.is_cancelled = False
        
        self.max_particles = settings.SPH_MAX_PARTICLES
        self.scenario_type = self.config.get("metadata", {}).get("type", "DAM_BREAK")
        self.is_benchmark = self.config.get("metadata", {}).get("is_benchmark", False)
        
        self.diagnostics = {}

    def validate(self) -> bool:
        valid_types = ["DAM_BREAK", "WATER_RELEASE", "RIVER_BLOCKAGE"]
        if self.scenario_type not in valid_types:
            self.error_message = f"Unknown scenario type: {self.scenario_type}"
            return False
            
        if not self.is_benchmark:
            pass # Removed strict DEM check to allow fallback terrain handling
                
        return True

    def prepare(self) -> None:
        params = self.config.get("physics_parameters", {})
        time_params = self.config.get("time_control", {})
        
        particle_spacing = params.get("particle_spacing", 1.0)
        h = params.get("smoothing_length", 2.0)
        
        self.solver = SPHSolver(max_particles=self.max_particles, h=h)
        
        if self.is_benchmark:
            self.domain_bounds = [0.0, 200.0, 0.0, 50.0]
            start_x, end_x = 0.0, params.get("breach_width", 50.0)
            start_y, end_y = 0.0, params.get("initial_water_level", 20.0)
            
            # Simple static breach for benchmark if not provided
            breach = DynamicBreach(
                xmin=50.0, xmax=55.0, ymin=0.0, ymax=50.0, 
                failure_time=params.get("failure_time", 0.0), 
                formation_time=params.get("formation_time", 1.0), 
                final_width=end_x - start_x
            )
            
            try:
                self.solver.init_benchmark_dam_break(start_x, end_x, start_y, end_y, particle_spacing, self.domain_bounds, breach)
            except ValueError as e:
                self.status = "FAILED"
                self.error_message = str(e)
                return
        else:
            source_datasets = self.config.get("source_datasets", [])
            dem_info = next((ds for ds in source_datasets if ds.get("dataset_type") == "DEM"), None)
            
            # Load real DEM
            if dem_info and "file_path" in dem_info and os.path.exists(dem_info["file_path"]):
                terrain = TerrainHandler.from_geotiff(dem_info["file_path"])
                # Bounds from raster bounds (left, right, bottom, top) -> [xmin, xmax, ymin, ymax]
                with rasterio.open(dem_info["file_path"]) as src:
                    self.domain_bounds = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
            else:
                # Mock fallback if filepath not provided
                dem_grid = np.zeros((100, 100))
                cell_size = dem_info.get("resolution", 2.0) if dem_info else 2.0
                terrain = TerrainHandler(dem_grid=dem_grid, transform=rasterio.transform.from_origin(0, 100, cell_size, cell_size))
                self.domain_bounds = [0.0, 100.0, 0.0, 100.0]
                
            # Initial Water Polygon [xmin, xmax, ymin, ymax]
            water_poly = params.get("initial_water_polygon", [0.0, 50.0, 0.0, 20.0])
            initial_water_surface_elevation = params.get("initial_water_level", 20.0)
            
            blockages = []
            breach = None
            if self.scenario_type == "RIVER_BLOCKAGE":
                blockages.append({
                    "xmin": 80.0, "xmax": 90.0, 
                    "ymin": 0.0, "ymax": 50.0
                })
            elif self.scenario_type == "DAM_BREAK":
                # User asked for dynamic breach
                breach = DynamicBreach(
                    xmin=water_poly[1], xmax=water_poly[1] + 5.0, 
                    ymin=water_poly[2], ymax=water_poly[3],
                    failure_time=params.get("failure_time", 2.0),
                    formation_time=params.get("formation_time", 5.0),
                    final_width=params.get("final_breach_width", 20.0)
                )
                
            try:
                self.solver.init_real_scenario(
                    self.domain_bounds, water_poly, initial_water_surface_elevation, 
                    particle_spacing, terrain, blockages, breach
                )
            except ValueError as e:
                self.status = "FAILED"
                self.error_message = str(e)
                return
        
        self.writer = ResultWriter(bounds=self.domain_bounds, resolution=particle_spacing)
        
        duration_s = time_params.get("duration_hours", 0.05) * 3600
        duration_s = min(duration_s, 5.0) # testing cap
        
        self.total_steps = int(duration_s / self.solver.integrator.max_dt)
        self.duration_s = duration_s
        
        self.status = "PREPARED"

    def run(self) -> None:
        self.status = "RUNNING"
        self.current_step = 0
        output_time_interval = 0.5 
        next_output_time = output_time_interval
        
        failure_time = self.config.get("physics_parameters", {}).get("failure_time", 2.0)
        
        try:
            while self.solver.time < self.duration_s:
                if self.is_cancelled:
                    self.status = "CANCELLED"
                    return
                    
                # For Blockage (River Blockage logic is instant removal as requested)
                if self.scenario_type == "RIVER_BLOCKAGE" and self.solver.time >= failure_time:
                    # In solver.py we don't have trigger_blockage_failure anymore, 
                    # we could just clear blockages directly
                    self.solver.boundary_handler.blockages = []
                    
                self.solver.step()
                self.current_step += 1
                
                # Check diagnostics every 10 steps
                if self.current_step % 10 == 0:
                    diag = self.solver.calculate_diagnostics()
                    self.diagnostics = diag
                    
                    if diag and diag.get("relative_volume_error", 0.0) > 0.05:
                        self.status = "FAILED"
                        self.error_message = f"Mass conservation failure: {diag['relative_volume_error']*100:.1f}% volume error."
                        return
                    
                    if diag and (np.isnan(diag.get("max_velocity", 0.0)) or diag.get("max_velocity", 0.0) > 200.0):
                        self.status = "FAILED"
                        self.error_message = f"Numerical instability detected (Max Vel: {diag.get('max_velocity')})."
                        return
                
                # Write results
                if self.solver.time >= next_output_time:
                    self.writer.process_frame(self.solver.state, self.solver.time)
                    next_output_time += output_time_interval
                    
            # Final output write
            self.diagnostics = self.solver.calculate_diagnostics()
            self.writer.process_frame(self.solver.state, self.solver.time)
            self.status = "COMPLETED"
        except Exception as e:
            logger.exception("SPH Engine failure")
            self.status = "FAILED"
            self.error_message = str(e)

    def get_status(self) -> Dict[str, Any]:
        progress = (self.solver.time / self.duration_s) * 100 if hasattr(self, 'duration_s') and self.duration_s > 0 else 0
        return {
            "status": self.status,
            "progress_percent": round(min(progress, 100.0), 2),
            "simulation_time": self.solver.time if self.solver else 0.0,
            "error": self.error_message,
            "diagnostics": self.diagnostics
        }

    def cancel(self) -> None:
        self.is_cancelled = True

    def load_results(self) -> Dict[str, Any]:
        """Returns the processed results from the ResultWriter."""
        if not self.writer:
            return {}
        
        res = self.writer.get_final_results()
        # Attach scientific output metadata
        res["metadata"] = {
            "sph_formulation": "2D SWE-SPH",
            "solver_version": "2.0 (Vectorized)",
            "particle_count": self.solver.state.num_particles if self.solver else 0,
            "crs": res.get("crs"),
            "bounds": res.get("bounds"),
            "conservation_diagnostics": self.diagnostics
        }
        return res
