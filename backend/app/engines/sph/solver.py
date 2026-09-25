import logging
import numpy as np
import abc
import rasterio
from app.engines.sph.particle import ParticleState, ParticleType
from app.engines.sph.kernel import CubicSplineKernel
from app.engines.sph.neighborhood import NeighborSearch
from app.engines.sph.physics import PhysicsSolver, Physics3DSolver
from app.engines.sph.boundary import BoundaryHandler, TerrainHandler, DynamicBreach
from app.engines.sph.integrator import TimeIntegrator

logger = logging.getLogger(__name__)

MAX_SPH_PARTICLES = 50000

class SPHSolverBase(abc.ABC):
    def __init__(self, max_particles: int, dim: int, h: float, rest_density: float, gravity: float, max_dt: float):
        self.dim = dim
        self.max_particles = max_particles
        self.state = ParticleState(max_particles, dim=dim)
        self.kernel = CubicSplineKernel(h=h, dim=dim)
        self.neighborhood = NeighborSearch(search_radius=2.0 * h)
        self.integrator = TimeIntegrator(max_dt=max_dt)
        self.boundary_handler = None
        self.terrain_handler = None
        self.time = 0.0
        self.initial_volume = 0.0

    def calculate_diagnostics(self):
        if self.state.num_particles == 0:
            return {"max_velocity": 0.0, "relative_volume_error": 0.0}
        vel = self.state.vel[:self.state.num_particles]
        return {
            "max_velocity": float(np.max(np.linalg.norm(vel, axis=1))),
            "relative_volume_error": 0.0 # simplified for now
        }

    @abc.abstractmethod
    def step(self):
        pass

class SPH2DSolver(SPHSolverBase):
    def __init__(self, max_particles: int = MAX_SPH_PARTICLES, h: float = 2.0, rest_density: float = 1000.0, gravity: float = 9.81, max_dt: float = 0.01):
        super().__init__(max_particles, 2, h, rest_density, gravity, max_dt)
        self.physics = PhysicsSolver(kernel=self.kernel, rest_density=rest_density, gravity=gravity)
        
    def init_benchmark_dam_break(self, start_x, end_x, start_y, end_y, spacing, bounds, breach=None):
        x = np.arange(start_x, end_x, spacing)
        y = np.arange(start_y, end_y, spacing)
        xx, yy = np.meshgrid(x, y)
        points = np.vstack((xx.ravel(), yy.ravel())).T
        
        N_req = len(points)
        if N_req > self.max_particles:
            raise ValueError(f"Requested particles ({N_req}) exceeds limit ({self.max_particles}).")
            
        volumes = np.full(N_req, spacing * spacing)
        masses = volumes * self.physics.rho0
        vels = np.zeros((N_req, 2))
        
        self.state.add_particles(points, vels, masses, ParticleType.FLUID)
        self.initial_volume = np.sum(volumes)
        
        self.boundary_handler = BoundaryHandler(bounds=bounds)
        if breach:
            self.boundary_handler.add_dynamic_breach(breach)
            
        # Create flat terrain for benchmark
        self.terrain_handler = TerrainHandler(dem_grid=np.zeros((2,2)), transform=rasterio.transform.from_origin(0, 50, 100, 50))
        
    def init_real_scenario(self, bounds: list, water_polygon: list, initial_water_surface_elevation: float, 
                           spacing: float, terrain_handler: TerrainHandler, blockages: list = [], breach: DynamicBreach = None):
        xmin, xmax, ymin, ymax = water_polygon
        x = np.arange(xmin, xmax, spacing)
        y = np.arange(ymin, ymax, spacing)
        xx, yy = np.meshgrid(x, y)
        candidates = np.vstack((xx.ravel(), yy.ravel())).T
        
        z_b, _ = terrain_handler.get_elevation_and_gradient(candidates)
        valid = z_b < initial_water_surface_elevation
        points = candidates[valid]
        z_b_valid = z_b[valid]
        
        N_req = len(points)
        if N_req > self.max_particles:
            raise ValueError(f"Requested particles ({N_req}) exceeds limit ({self.max_particles}). Try increasing spacing.")
            
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

    def step(self):
        if self.state.num_particles == 0:
            return
            
        fluid_idx = self.state.get_fluid_indices()
        self.neighborhood.build_tree(self.state.pos[fluid_idx])
        i, j = self.neighborhood.query_pairs()
        
        self.physics.compute_density_and_pressure(self.state, i, j)
        self.physics.compute_forces(self.state, i, j)
        
        z_b, grad_z = self.terrain_handler.get_elevation_and_gradient(self.state.pos[fluid_idx])
        self.state.z_b[fluid_idx] = z_b
        
        grad_z = np.nan_to_num(grad_z, nan=0.0, posinf=1.0, neginf=-1.0)
        grad_z = np.clip(grad_z, -2.0, 2.0)
        
        self.state.acc[fluid_idx, 0] += -self.physics.gravity * grad_z[:, 0]
        self.state.acc[fluid_idx, 1] += -self.physics.gravity * grad_z[:, 1]
        
        dt = self.integrator.compute_timestep(self.state, self.physics)
        self.integrator.step(dt, self.state, self.boundary_handler, self.time)
        
        self.time += dt

class SPH3DSolver(SPHSolverBase):
    def __init__(self, max_particles: int = MAX_SPH_PARTICLES, h: float = 2.0, rest_density: float = 1000.0, gravity: float = 9.81, max_dt: float = 0.01):
        super().__init__(max_particles, 3, h, rest_density, gravity, max_dt)
        self.physics = Physics3DSolver(kernel=self.kernel, rest_density=rest_density, gravity=gravity)

    def init_real_scenario(self, bounds: list, water_polygon: list, initial_water_surface_elevation: float, 
                           spacing: float, terrain_handler: TerrainHandler, blockages: list = [], breach: DynamicBreach = None):
        xmin, xmax, ymin, ymax = water_polygon
        x = np.arange(xmin, xmax, spacing)
        y = np.arange(ymin, ymax, spacing)
        xx, yy = np.meshgrid(x, y)
        candidates_2d = np.vstack((xx.ravel(), yy.ravel())).T
        
        z_b, _ = terrain_handler.get_elevation_and_gradient(candidates_2d)
        valid_2d = z_b < initial_water_surface_elevation
        
        points_2d = candidates_2d[valid_2d]
        z_b_valid = z_b[valid_2d]
        
        points_3d = []
        for i in range(len(points_2d)):
            px, py = points_2d[i]
            bed_z = z_b_valid[i]
            # Fill vertically
            z = bed_z + spacing/2.0
            while z < initial_water_surface_elevation:
                points_3d.append([px, py, z])
                z += spacing
                
        points_3d = np.array(points_3d)
        N_req = len(points_3d)
        if N_req > self.max_particles:
            raise ValueError(f"Requested particles ({N_req}) exceeds 3D limit ({self.max_particles}).")
            
        logger.info(f"Initialized {N_req} 3D particles.")
        mass_val = (spacing**3) * self.physics.rho0
        masses = np.full(N_req, mass_val)
        vels = np.zeros((N_req, 3))
        
        self.state.add_particles(points_3d, vels, masses, ParticleType.FLUID)
        self.initial_volume = N_req * (spacing**3)
        
        self.boundary_handler = BoundaryHandler(bounds=bounds)
        for block in blockages:
            self.boundary_handler.add_blockage(**block)
            
        if breach:
            self.boundary_handler.add_dynamic_breach(breach)
            
        self.terrain_handler = terrain_handler
        
    def step(self):
        if self.state.num_particles == 0:
            return
            
        fluid_idx = self.state.get_fluid_indices()
        
        # Terrain collision penalty logic
        pos_2d = self.state.pos[fluid_idx, :2]
        z_b, grad_z = self.terrain_handler.get_elevation_and_gradient(pos_2d)
        
        # Particles below terrain get pushed up
        below_terrain = self.state.pos[fluid_idx, 2] < z_b
        if np.any(below_terrain):
            idx_below = fluid_idx[below_terrain]
            self.state.pos[idx_below, 2] = z_b[below_terrain]
            # Zero out vertical velocity if going down
            self.state.vel[idx_below, 2] = np.maximum(0, self.state.vel[idx_below, 2])
            
        self.neighborhood.build_tree(self.state.pos[fluid_idx])
        i, j = self.neighborhood.query_pairs()
        
        self.physics.compute_density_and_pressure(self.state, i, j)
        self.physics.compute_forces(self.state, i, j)
        
        dt = self.integrator.compute_timestep(self.state, self.physics)
        self.integrator.step(dt, self.state, self.boundary_handler, self.time)
        
        self.time += dt
