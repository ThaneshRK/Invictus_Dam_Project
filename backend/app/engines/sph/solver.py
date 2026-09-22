import logging
import numpy as np
from app.engines.sph.particle import ParticleState, ParticleType
from app.engines.sph.kernel import CubicSplineKernel
from app.engines.sph.neighborhood import NeighborSearch
from app.engines.sph.physics import PhysicsSolver
from app.engines.sph.boundary import BoundaryHandler, TerrainHandler, DynamicBreach
from app.engines.sph.integrator import TimeIntegrator

logger = logging.getLogger(__name__)

MAX_SPH_PARTICLES = 50000

class SPHSolver:
    """
    Main orchestrator for the modular SPH engine.
    Combines ParticleState, Physics, Boundary, and Time integration.
    """
    def __init__(self, max_particles: int = MAX_SPH_PARTICLES, h: float = 2.0, rest_density: float = 1000.0, 
                 gravity: float = 9.81, max_dt: float = 0.01):
        
        self.max_particles = max_particles
        self.state = ParticleState(max_particles)
        self.kernel = CubicSplineKernel(h=h)
        self.neighborhood = NeighborSearch(search_radius=2.0 * h)
        self.physics = PhysicsSolver(kernel=self.kernel, rest_density=rest_density, gravity=gravity)
        self.integrator = TimeIntegrator(max_dt=max_dt)
        
        self.boundary_handler = None
        self.terrain_handler = None
        self.time = 0.0
        
        self.initial_volume = 0.0

    def init_benchmark_dam_break(self, start_x: float, end_x: float, start_y: float, end_y: float, 
                                 spacing: float, bounds: list, breach: DynamicBreach = None):
        """
        Analytical benchmark mode initialization (no DEM).
        """
        x = np.arange(start_x, end_x, spacing)
        y = np.arange(start_y, end_y, spacing)
        xx, yy = np.meshgrid(x, y)
        points = np.vstack((xx.ravel(), yy.ravel())).T
        
        N_req = len(points)
        if N_req > self.max_particles:
            raise ValueError(f"Requested particles ({N_req}) exceeds limit ({self.max_particles})")
            
        mass_val = spacing * spacing * self.physics.rho0
        masses = np.full(N_req, mass_val)
        vels = np.zeros((N_req, 2))
        
        self.state.add_particles(points, vels, masses, ParticleType.FLUID)
        
        # Approximate initial volume for SWE: mass / rho0
        self.initial_volume = np.sum(masses) / self.physics.rho0
        
        self.boundary_handler = BoundaryHandler(bounds=bounds)
        if breach:
            self.boundary_handler.add_dynamic_breach(breach)
            
        # Dummy terrain handler (flat)
        self.terrain_handler = TerrainHandler(np.zeros((2,2)), transform=[1,0,0,0,-1,0], nodata=None)

    def init_real_scenario(self, bounds: list, water_polygon: list, initial_water_surface_elevation: float, 
                           spacing: float, terrain_handler: TerrainHandler, blockages: list = [], breach: DynamicBreach = None):
        """
        Real scenario mode initialization using DEM and scenario boundaries.
        water_polygon: [xmin, xmax, ymin, ymax]
        """
        xmin, xmax, ymin, ymax = water_polygon
        
        # Grid sampling for candidates
        x = np.arange(xmin, xmax, spacing)
        y = np.arange(ymin, ymax, spacing)
        xx, yy = np.meshgrid(x, y)
        candidates = np.vstack((xx.ravel(), yy.ravel())).T
        
        # Filter candidates based on DEM
        z_b, _ = terrain_handler.get_elevation_and_gradient(candidates)
        
        valid = z_b < initial_water_surface_elevation
        points = candidates[valid]
        z_b_valid = z_b[valid]
        
        N_req = len(points)
        if N_req > self.max_particles:
            raise ValueError(f"Requested particles ({N_req}) exceeds limit ({self.max_particles}). Try increasing spacing.")
            
        logger.info(f"Initialized {N_req} particles for real scenario.")
        
        # Each particle represents a volume of water: area * depth
        # Depth = surface_elevation - bed_elevation
        depths = initial_water_surface_elevation - z_b_valid
        volumes = (spacing * spacing) * depths
        masses = volumes * self.physics.rho0
        vels = np.zeros((N_req, 2))
        
        self.state.add_particles(points, vels, masses, ParticleType.FLUID)
        
        self.initial_volume = np.sum(volumes)
        
        self.boundary_handler = BoundaryHandler(bounds=bounds)
        for block in blockages:
            self.boundary_handler.add_blockage(**block)
            
        if breach:
            self.boundary_handler.add_dynamic_breach(breach)
            
        self.terrain_handler = terrain_handler

    def calculate_diagnostics(self) -> dict:
        """
        Computes conservation and stability diagnostics.
        """
        fluid_idx = self.state.get_fluid_indices()
        if len(fluid_idx) == 0:
            return {}
            
        current_mass = np.sum(self.state.mass[fluid_idx])
        current_volume = current_mass / self.physics.rho0
        
        abs_err = current_volume - self.initial_volume
        rel_err = abs_err / self.initial_volume if self.initial_volume > 0 else 0
        
        max_vel = np.max(np.linalg.norm(self.state.vel[fluid_idx], axis=1))
        
        return {
            "initial_volume": self.initial_volume,
            "current_volume": current_volume,
            "absolute_volume_error": abs_err,
            "relative_volume_error": rel_err,
            "max_velocity": float(max_vel),
            "particle_count": len(fluid_idx)
        }

    def step(self):
        """
        Executes a single simulation timestep.
        """
        if self.state.num_particles == 0:
            return
            
        fluid_idx = self.state.get_fluid_indices()
        
        # 1. Neighbor Search
        self.neighborhood.build_tree(self.state.pos[fluid_idx])
        i, j = self.neighborhood.query_pairs()
        
        # 2. Compute Density and Pressure
        self.physics.compute_density_and_pressure(self.state, i, j)
        
        # 3. Compute Forces
        self.physics.compute_forces(self.state, i, j)
        
        # 4. Apply Terrain Gradient (Gravity on DEM slope)
        z_b, grad_z = self.terrain_handler.get_elevation_and_gradient(self.state.pos[fluid_idx])
        self.state.z_b[fluid_idx] = z_b
        
        # Sanitize terrain gradient to avoid numerical spikes on sharp slopes
        grad_z = np.nan_to_num(grad_z, nan=0.0, posinf=1.0, neginf=-1.0)
        grad_z = np.clip(grad_z, -2.0, 2.0)
        
        # Acceleration due to bed slope: -g * grad_z_b
        self.state.acc[fluid_idx, 0] += -self.physics.gravity * grad_z[:, 0]
        self.state.acc[fluid_idx, 1] += -self.physics.gravity * grad_z[:, 1]
        
        # 5. Time Integration
        dt = self.integrator.compute_timestep(self.state, self.physics)
        self.integrator.step(dt, self.state, self.boundary_handler, self.time)
        
        self.time += dt
