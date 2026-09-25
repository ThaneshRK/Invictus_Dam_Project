import logging
import uuid
import numpy as np
import os
import rasterio
from typing import Dict, Any
from app.engines.base import SimulationEngine
from app.engines.sph.solver import SPHSolverBase, SPH2DSolver, SPH3DSolver
from app.engines.sph.boundary import TerrainHandler, DynamicBreach
from app.engines.sph.writer import ResultWriter
from app.engines.sph.builder import SPHInputBuilder
from app.core.config import settings

logger = logging.getLogger(__name__)

class SPHEngine(SimulationEngine):
    """
    SPH Simulation Engine Implementation.
    Orchestrates the modular solver, inputs, and outputs.
    """
    def __init__(self, context: Any):
        super().__init__(context)
        self.solver = None
        self.writer = None
        self.domain_bounds = [0.0, 100.0, 0.0, 100.0]
        
        self.current_step = 0
        self.total_steps = 0
        self.output_interval_steps = 100
        self.is_cancelled = False
        
        self.max_particles = settings.SPH_MAX_PARTICLES
        st = self.context.scenario.scenario_type
        self.scenario_type = st.value if hasattr(st, 'value') else str(st)
        self.is_benchmark = False # Benchmarks should use a different testing engine path now
        
        self.diagnostics = {}

    def validate(self) -> bool:
        valid_types = ["DAM_BREAK", "WATER_RELEASE", "RIVER_BLOCKAGE"]
        if self.scenario_type not in valid_types:
            self.error_message = f"Unknown scenario type: {self.scenario_type}"
            return False
        return True

    def prepare(self) -> None:
        if self.is_benchmark:
            # Benchmark specific initialization
            self.domain_bounds = [0.0, 200.0, 0.0, 50.0]
            particle_spacing = self.context.scenario.parameters.get("particle_spacing", 1.0) if self.context.scenario.parameters else 1.0
            h = self.context.scenario.parameters.get("smoothing_length", 2.0) if self.context.scenario.parameters else 2.0
            self.solver = SPH2DSolver(max_particles=self.max_particles, h=h)
            
            start_x, end_x = 0.0, self.context.scenario.parameters.get("breach_width", 50.0) if self.context.scenario.parameters else 50.0
            start_y, end_y = 0.0, self.context.scenario.parameters.get("initial_water_level", 20.0) if self.context.scenario.parameters else 20.0
            
            breach = DynamicBreach(
                xmin=50.0, xmax=55.0, ymin=0.0, ymax=50.0,
                failure_time=self.context.scenario.parameters.get("failure_time", 0.0) if self.context.scenario.parameters else 0.0,
                formation_time=self.context.scenario.parameters.get("formation_time", 1.0) if self.context.scenario.parameters else 1.0,
                final_width=end_x - start_x
            )
            try:
                self.solver.init_benchmark_dam_break(start_x, end_x, start_y, end_y, particle_spacing, self.domain_bounds, breach)
            except ValueError as e:
                self.status = "FAILED"
                self.error_message = str(e)
                return
            
            self.writer = ResultWriter(bounds=self.domain_bounds, resolution=particle_spacing)
            duration_s = self.context.scenario.simulation_duration * 3600
            duration_s = min(duration_s, 5.0)
            self.total_steps = int(duration_s / self.solver.integrator.max_dt)
            self.duration_s = duration_s
            self.status = "PREPARED"
            return

        try:
            builder = SPHInputBuilder(self.context)
            inputs = builder.build()
        except ValueError as e:
            self.status = "FAILED"
            self.error_message = str(e)
            return
            
        self.domain_bounds = inputs["domain_bounds"]
        particle_spacing = inputs["particle_spacing"]
        h = inputs["smoothing_length"]
        
        # Determine 2D vs 3D based on context engine choice if needed, but default 2D
        self.solver = SPH2DSolver(max_particles=self.max_particles, h=h)
        
        try:
            self.solver.init_real_scenario(
                self.domain_bounds, 
                inputs["water_poly"], 
                inputs["initial_water_level"], 
                particle_spacing, 
                inputs["terrain"], 
                inputs["blockages"], 
                inputs["breach"]
            )
        except ValueError as e:
            self.status = "FAILED"
            self.error_message = str(e)
            return
        
        self.writer = ResultWriter(bounds=self.domain_bounds, resolution=particle_spacing)
        
        duration_s = inputs["duration_s"]
        duration_s = min(duration_s, 5.0) # testing cap
        
        self.total_steps = int(duration_s / self.solver.integrator.max_dt)
        self.duration_s = duration_s
        
        self.status = "PREPARED"

    def run(self) -> None:
        self.status = "RUNNING"
        self.current_step = 0
        output_time_interval = 0.5 
        next_output_time = output_time_interval
        
        failure_time = self.context.scenario.parameters.get("failure_time", 2.0) if self.context.scenario.parameters else 2.0
        
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
