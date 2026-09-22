import numpy as np
from app.engines.sph.particle import ParticleState
from app.engines.sph.physics import PhysicsSolver
from app.engines.sph.boundary import BoundaryHandler

class TimeIntegrator:
    """
    Handles time stepping using Semi-Implicit Euler integration.
    """
    def __init__(self, max_dt: float = 0.01, cfl_factor: float = 0.2):
        self.max_dt = max_dt
        self.cfl_factor = cfl_factor

    def compute_timestep(self, state: ParticleState, physics: PhysicsSolver) -> float:
        """
        Computes stable timestep based on CFL condition and forces.
        """
        N = state.num_particles
        if N == 0:
            return self.max_dt
            
        fluid_idx = state.get_fluid_indices()
        if len(fluid_idx) == 0:
            return self.max_dt
            
        max_vel = np.max(np.linalg.norm(state.vel[fluid_idx], axis=1))
        max_acc = np.max(np.linalg.norm(state.acc[fluid_idx], axis=1))
        
        # Speed of sound for artificial viscosity calculation
        c = np.sqrt(7.0 * physics.stiffness / physics.rho0)
        
        dt_cfl = self.max_dt
        if max_vel > 0:
            dt_cfl = self.cfl_factor * physics.kernel.h / (c + max_vel)
            
        dt_force = self.max_dt
        if max_acc > 0 and not np.isnan(max_acc):
            dt_force = 0.25 * np.sqrt(physics.kernel.h / min(max_acc, 200.0))
            
        calculated = min(self.max_dt, dt_cfl, dt_force)
        return max(calculated, 0.0001)

    def step(self, dt: float, state: ParticleState, boundary: BoundaryHandler, current_time: float = 0.0):
        """
        Advances particle positions and velocities.
        (Semi-Implicit Euler: update velocity with acc, then position with new vel)
        """
        fluid_idx = state.get_fluid_indices()
        if len(fluid_idx) == 0:
            return
        
        # Clip acceleration spikes
        np.clip(state.acc[fluid_idx], -200.0, 200.0, out=state.acc[fluid_idx])
        
        # v(t + dt) = v(t) + a(t) * dt
        state.vel[fluid_idx] += state.acc[fluid_idx] * dt
        
        # Physical velocity limit (max ~30 m/s for flood waves)
        speeds = np.linalg.norm(state.vel[fluid_idx], axis=1)
        max_phys_speed = 30.0
        exceeded = speeds > max_phys_speed
        if np.any(exceeded):
            state.vel[fluid_idx[exceeded]] *= (max_phys_speed / speeds[exceeded])[:, np.newaxis]
        
        # x(t + dt) = x(t) + v(t + dt) * dt
        state.pos[fluid_idx] += state.vel[fluid_idx] * dt
        
        # Apply boundary constraints immediately after moving
        boundary.enforce_boundaries(state, current_time)
