import numpy as np
from app.engines.sph.particle import ParticleState, ParticleType
from app.engines.sph.kernel import CubicSplineKernel

class PhysicsSolver:
    """
    Computes SPH physics: Density, Pressure, and Forces (including artificial viscosity).
    """
    def __init__(self, kernel: CubicSplineKernel, rest_density: float = 1000.0, stiffness: float = 50000.0, gravity: float = 9.81, dynamic_viscosity: float = 0.01):
        self.kernel = kernel
        self.rho0 = rest_density
        self.stiffness = stiffness
        self.gravity = gravity
        
        # Artificial viscosity parameters (Monaghan 1992)
        self.alpha_visc = 0.1
        self.beta_visc = 0.1
        self.epsilon = 0.01 * (kernel.h ** 2)

    def compute_density_and_pressure(self, state: ParticleState, neighbors: list):
        """
        Calculates density and pressure for fluid particles.
        """
        N = state.num_particles
        
        # Reset density
        state.rho[:N] = 0.0
        
        for i in range(N):
            # Summation for density
            rho_i = 0.0
            for j in neighbors[i]:
                r_vec = state.pos[i] - state.pos[j]
                r = np.linalg.norm(r_vec)
                rho_i += state.mass[j] * self.kernel.W(r)
                
            # Free surface correction - prevent density from dropping below rest density
            state.rho[i] = max(rho_i, self.rho0)
            
            # 2D Shallow Water Equations (SWE-SPH) hydrostatic pressure: P = 0.5 * g * rho0 * h^2
            h_depth = state.rho[i] / self.rho0
            state.press[i] = 0.5 * self.gravity * self.rho0 * (h_depth**2)
            state.press[i] = max(state.press[i], 0.0)

    def compute_forces(self, state: ParticleState, neighbors: list):
        """
        Computes accelerations from pressure gradient, gravity, and artificial viscosity.
        """
        N = state.num_particles
        fluid_idx = state.get_fluid_indices()
        
        # Reset acceleration
        state.acc[:N] = 0.0
        # Apply gravity to fluid particles
        state.acc[fluid_idx, 1] = -self.gravity
        
        h = self.kernel.h
        
        for i in fluid_idx:
            acc_i = np.zeros(2, dtype=np.float64)
            rho_i = state.rho[i]
            p_i = state.press[i]
            pos_i = state.pos[i]
            vel_i = state.vel[i]
            
            # Sound speed for artificial viscosity
            c_i = np.sqrt((7.0 * self.stiffness) / self.rho0)
            
            for j in neighbors[i]:
                if i == j:
                    continue
                    
                pos_j = state.pos[j]
                r_vec = pos_i - pos_j
                r = np.linalg.norm(r_vec)
                
                if r > 0 and r <= 2 * h:
                    rho_j = state.rho[j]
                    p_j = state.press[j]
                    vel_j = state.vel[j]
                    v_vec = vel_i - vel_j
                    
                    grad_W = self.kernel.grad_W(r_vec, r)
                    
                    # Pressure force
                    pressure_term = (p_i / (rho_i**2)) + (p_j / (rho_j**2))
                    
                    # Artificial viscosity (Monaghan)
                    pi_ij = 0.0
                    v_dot_r = np.dot(v_vec, r_vec)
                    if v_dot_r < 0:
                        c_j = np.sqrt((7.0 * self.stiffness) / self.rho0)
                        c_ij = 0.5 * (c_i + c_j)
                        rho_ij = 0.5 * (rho_i + rho_j)
                        mu_ij = (h * v_dot_r) / (r**2 + self.epsilon)
                        pi_ij = (-self.alpha_visc * c_ij * mu_ij + self.beta_visc * mu_ij**2) / rho_ij
                    
                    # Total force contribution
                    acc_i -= state.mass[j] * (pressure_term + pi_ij) * grad_W
                    
            state.acc[i] += acc_i
