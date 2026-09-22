import numpy as np

class ParticleType:
    FLUID = 0
    BOUNDARY = 1
    # Adding more types if needed, like DEM boundaries

class ParticleState:
    """
    Holds the physical state of all particles in the SPH simulation using efficient NumPy arrays.
    """
    def __init__(self, max_particles: int):
        self.max_particles = max_particles
        self.num_particles = 0
        
        # Core physical properties
        self.pos = np.zeros((max_particles, 2), dtype=np.float64)
        self.vel = np.zeros((max_particles, 2), dtype=np.float64)
        self.acc = np.zeros((max_particles, 2), dtype=np.float64)
        
        self.mass = np.zeros(max_particles, dtype=np.float64)
        self.rho = np.zeros(max_particles, dtype=np.float64)
        self.press = np.zeros(max_particles, dtype=np.float64)
        
        # SWE-SPH specific variables
        self.h_depth = np.zeros(max_particles, dtype=np.float64) # water depth h
        self.z_b = np.zeros(max_particles, dtype=np.float64)     # bed elevation
        
        # Diagnostics
        self.arrival_time = np.full(max_particles, -1.0, dtype=np.float64)
        
        # State tracking
        self.active = np.zeros(max_particles, dtype=bool)
        
        # Type indicator (fluid vs boundary)
        self.type = np.full(max_particles, ParticleType.FLUID, dtype=np.int32)
        
    def add_particles(self, pos: np.ndarray, vel: np.ndarray, mass: np.ndarray, ptype: int) -> None:
        """
        Adds a batch of particles.
        """
        count = len(pos)
        if self.num_particles + count > self.max_particles:
            raise ValueError(f"Cannot add {count} particles. Exceeds max limit of {self.max_particles}.")
            
        start = self.num_particles
        end = start + count
        
        self.pos[start:end] = pos
        self.vel[start:end] = vel
        self.mass[start:end] = mass
        self.type[start:end] = ptype
        self.active[start:end] = True
        
        self.num_particles += count
        
    def get_fluid_indices(self) -> np.ndarray:
        return np.where((self.type[:self.num_particles] == ParticleType.FLUID) & self.active[:self.num_particles])[0]

    def get_boundary_indices(self) -> np.ndarray:
        return np.where((self.type[:self.num_particles] == ParticleType.BOUNDARY) & self.active[:self.num_particles])[0]
