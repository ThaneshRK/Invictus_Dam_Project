import numpy as np
from app.engines.sph.particle import ParticleState, ParticleType
from app.engines.sph.kernel import CubicSplineKernel

class PhysicsSolver:
    """
    Computes 2D depth-averaged SWE-SPH physics: Density, Pressure, and Forces (including artificial viscosity).
    Vectorized implementation using pair indexing.
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

    def compute_density_and_pressure(self, state: ParticleState, i: np.ndarray, j: np.ndarray):
        """
        Calculates density and pressure for fluid particles using vectorized pairwise interactions.
        """
        N = state.num_particles
        fluid_idx = state.get_fluid_indices()
        
        # Reset density
        state.rho[:N] = 0.0
        
        if len(i) > 0:
            pos_i = state.pos[i]
            pos_j = state.pos[j]
            mass_j = state.mass[j]
            
            r_vec = pos_i - pos_j
            r = np.linalg.norm(r_vec, axis=1)
            
            W_r = self.kernel.W(r)
            rho_contrib = mass_j * W_r
            
            # Accumulate density contributions
            np.add.at(state.rho, i, rho_contrib)
            
        # Add self-density for isolated particles (W(0))
        W_0 = self.kernel.W(np.array([0.0]))[0]
        state.rho[fluid_idx] += state.mass[fluid_idx] * W_0
            
        # Free surface correction - prevent density from dropping below rest density
        state.rho[fluid_idx] = np.maximum(state.rho[fluid_idx], self.rho0)
        
        # SWE Depth conversion: h = rho / rho0
        state.h_depth[fluid_idx] = state.rho[fluid_idx] / self.rho0
        
        # 2D Shallow Water Equations (SWE-SPH) hydrostatic pressure: P = 0.5 * g * rho0 * h^2
        state.press[fluid_idx] = 0.5 * self.gravity * self.rho0 * (state.h_depth[fluid_idx]**2)
        state.press[fluid_idx] = np.maximum(state.press[fluid_idx], 0.0)

    def compute_forces(self, state: ParticleState, i: np.ndarray, j: np.ndarray):
        """
        Computes accelerations from pressure gradient, gravity, and artificial viscosity.
        Vectorized using pairwise interactions.
        """
        N = state.num_particles
        fluid_idx = state.get_fluid_indices()
        
        # Reset acceleration
        state.acc[:N] = 0.0
        # Apply gravity (handled by terrain gradient in solver, here we just set base if needed, but in SWE it's pressure + bed slope)
        if getattr(self, 'vertical_2d', False):
            state.acc[fluid_idx, 1] = -self.gravity
        
        if len(i) > 0:
            h = self.kernel.h
            
            # Filter valid interactions (i != j and r <= 2h)
            mask = i != j
            i_m = i[mask]
            j_m = j[mask]
            
            pos_i = state.pos[i_m]
            pos_j = state.pos[j_m]
            r_vec = pos_i - pos_j
            r = np.linalg.norm(r_vec, axis=1)
            
            mask_r = (r > 0) & (r <= 2 * h)
            i_m = i_m[mask_r]
            j_m = j_m[mask_r]
            r_vec = r_vec[mask_r]
            r = r[mask_r]
            
            if len(i_m) > 0:
                rho_i = state.rho[i_m]
                rho_j = state.rho[j_m]
                p_i = state.press[i_m]
                p_j = state.press[j_m]
                vel_i = state.vel[i_m]
                vel_j = state.vel[j_m]
                
                v_vec = vel_i - vel_j
                grad_W = self.kernel.grad_W(r_vec, r)
                
                # Pressure force
                pressure_term = (p_i / (rho_i**2)) + (p_j / (rho_j**2))
                
                # Artificial viscosity (Monaghan)
                pi_ij = np.zeros(len(i_m), dtype=np.float64)
                v_dot_r = np.sum(v_vec * r_vec, axis=1)
                
                visc_mask = v_dot_r < 0
                
                if np.any(visc_mask):
                    v_dot_r_v = v_dot_r[visc_mask]
                    rho_i_v = rho_i[visc_mask]
                    rho_j_v = rho_j[visc_mask]
                    r_v = r[visc_mask]
                    
                    c_i = np.sqrt((7.0 * self.stiffness) / self.rho0)
                    c_ij = c_i  # Constant sound speed assumption based on stiffness/rho0
                    
                    rho_ij = 0.5 * (rho_i_v + rho_j_v)
                    mu_ij = (h * v_dot_r_v) / (r_v**2 + self.epsilon)
                    
                    pi_ij[visc_mask] = (-self.alpha_visc * c_ij * mu_ij + self.beta_visc * mu_ij**2) / rho_ij
                
                # Total force contribution
                total_term = pressure_term + pi_ij
                mass_j = state.mass[j_m]
                
                acc_contrib = -mass_j[:, np.newaxis] * total_term[:, np.newaxis] * grad_W
                
                # Accumulate
                np.add.at(state.acc[:, 0], i_m, acc_contrib[:, 0])
                np.add.at(state.acc[:, 1], i_m, acc_contrib[:, 1])


class Physics3DSolver(PhysicsSolver):
    """
    Computes true 3D SPH physics: Density, Pressure, Forces.
    """
    def __init__(self, kernel: CubicSplineKernel, rest_density: float = 1000.0, stiffness: float = 50000.0, gravity: float = 9.81, dynamic_viscosity: float = 0.01):
        super().__init__(kernel, rest_density, stiffness, gravity, dynamic_viscosity)
        self.gamma = 7.0
        self.B = (self.rho0 * (10.0 * self.gravity * self.kernel.h)) / self.gamma # Tait eq constant approximation
        
    def compute_density_and_pressure(self, state: ParticleState, i: np.ndarray, j: np.ndarray):
        N = state.num_particles
        fluid_idx = state.get_fluid_indices()
        
        # Density summation via bincount (buffered scatter — mathematically identical
        # to np.add.at but 10-50x faster for large pair lists)
        if len(i) > 0:
            pos_i = state.pos[i]
            pos_j = state.pos[j]
            mass_j = state.mass[j]
            
            r_vec = pos_i - pos_j
            r = np.sqrt(np.einsum('ij,ij->i', r_vec, r_vec))
            
            W_r = self.kernel.W(r)
            rho_contrib = mass_j * W_r
            state.rho[:N] = np.bincount(i, weights=rho_contrib, minlength=N)[:N]
        else:
            state.rho[:N] = 0.0
        
        W_0 = self.kernel.W(0.0)
        if isinstance(W_0, np.ndarray):
            W_0 = W_0[0]
        state.rho[fluid_idx] += state.mass[fluid_idx] * W_0
        
        # Free surface & boundary
        state.rho[fluid_idx] = np.maximum(state.rho[fluid_idx], self.rho0)
        
        # Tait equation for 3D water
        ratio = state.rho[fluid_idx] / self.rho0
        state.press[fluid_idx] = self.B * (ratio**self.gamma - 1.0)
        state.press[fluid_idx] = np.maximum(state.press[fluid_idx], 0.0)

    def compute_forces(self, state: ParticleState, i: np.ndarray, j: np.ndarray):
        N = state.num_particles
        fluid_idx = state.get_fluid_indices()
        
        state.acc[:N] = 0.0
        # True 3D gravity (assuming Z is up)
        state.acc[fluid_idx, 2] = -self.gravity
        
        if len(i) > 0:
            h = self.kernel.h
            # query_pairs() only yields distinct pairs within the 2h support radius,
            # so no self-pair / out-of-support masking is needed here.
            i_m = i
            j_m = j
            
            pos_i = state.pos[i_m]
            pos_j = state.pos[j_m]
            r_vec = pos_i - pos_j
            r = np.sqrt(np.einsum('ij,ij->i', r_vec, r_vec))
            
            if len(i_m) > 0:
                rho_i = state.rho[i_m]
                rho_j = state.rho[j_m]
                p_i = state.press[i_m]
                p_j = state.press[j_m]
                vel_i = state.vel[i_m]
                vel_j = state.vel[j_m]
                
                v_vec = vel_i - vel_j
                grad_W = self.kernel.grad_W(r_vec, r)
                
                pressure_term = (p_i / (rho_i**2)) + (p_j / (rho_j**2))
                
                pi_ij = np.zeros(len(i_m), dtype=np.float64)
                v_dot_r = np.einsum('ij,ij->i', v_vec, r_vec)
                visc_mask = v_dot_r < 0
                
                if np.any(visc_mask):
                    v_dot_r_v = v_dot_r[visc_mask]
                    rho_i_v = rho_i[visc_mask]
                    rho_j_v = rho_j[visc_mask]
                    r_v = r[visc_mask]
                    
                    c_ij = np.sqrt(self.gamma * self.B / self.rho0)
                    rho_ij = 0.5 * (rho_i_v + rho_j_v)
                    mu_ij = (h * v_dot_r_v) / (r_v**2 + self.epsilon)
                    
                    pi_ij[visc_mask] = (-self.alpha_visc * c_ij * mu_ij + self.beta_visc * mu_ij**2) / rho_ij
                
                total_term = pressure_term + pi_ij
                mass_j = state.mass[j_m]
                
                acc_contrib = -mass_j[:, np.newaxis] * total_term[:, np.newaxis] * grad_W
                
                # Buffered scatter (identical accumulation, far faster than np.add.at)
                for k in range(3):
                    state.acc[:N, k] += np.bincount(
                        i_m, weights=acc_contrib[:, k], minlength=N
                    )
