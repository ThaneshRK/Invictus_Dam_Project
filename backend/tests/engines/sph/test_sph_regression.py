import pytest
import numpy as np
from app.engines.sph.particle import ParticleState, ParticleType
from app.engines.sph.kernel import CubicSplineKernel
from app.engines.sph.neighborhood import NeighborSearch
from app.engines.sph.physics import PhysicsSolver as VectorizedPhysics
from tests.engines.sph.legacy_physics import PhysicsSolver as LegacyPhysics

def setup_deterministic_particles(N=1000):
    state = ParticleState(N)
    
    # Create a grid of particles
    grid_size = int(np.ceil(np.sqrt(N)))
    spacing = 1.0
    
    x = np.linspace(0, grid_size * spacing, grid_size)
    y = np.linspace(0, grid_size * spacing, grid_size)
    xx, yy = np.meshgrid(x, y)
    
    pos = np.vstack((xx.ravel(), yy.ravel())).T[:N]
    vel = np.random.RandomState(42).uniform(-1, 1, (N, 2))
    mass = np.full(N, 1000.0 * spacing * spacing) # rho0 = 1000
    
    state.add_particles(pos, vel, mass, ParticleType.FLUID)
    return state

def test_physics_vectorization_regression():
    N = 400
    h = 2.0
    
    state_legacy = setup_deterministic_particles(N)
    state_vectorized = setup_deterministic_particles(N)
    
    kernel = CubicSplineKernel(h=h)
    
    neighborhood = NeighborSearch(search_radius=2.0 * h)
    neighborhood.build_tree(state_legacy.pos[:N])
    
    # legacy physics uses the legacy neighborhood method
    # so we need to generate legacy_neighbors
    legacy_neighbors = neighborhood.tree.query_ball_point(state_legacy.pos[:N], neighborhood.search_radius)
    
    # Vectorized physics needs pairs
    i, j = neighborhood.query_pairs()
    
    legacy_physics = LegacyPhysics(kernel=kernel)
    vectorized_physics = VectorizedPhysics(kernel=kernel)
    legacy_physics.vertical_2d = True
    vectorized_physics.vertical_2d = True
    
    # 1. Density and Pressure
    legacy_physics.compute_density_and_pressure(state_legacy, legacy_neighbors)
    vectorized_physics.compute_density_and_pressure(state_vectorized, i, j)
    
    np.testing.assert_allclose(state_vectorized.rho[:N], state_legacy.rho[:N], rtol=1e-5, err_msg="Density mismatch")
    np.testing.assert_allclose(state_vectorized.press[:N], state_legacy.press[:N], rtol=1e-5, err_msg="Pressure mismatch")
    
    # 2. Forces
    legacy_physics.compute_forces(state_legacy, legacy_neighbors)
    vectorized_physics.compute_forces(state_vectorized, i, j)
    
    np.testing.assert_allclose(state_vectorized.acc[:N], state_legacy.acc[:N], rtol=1e-5, err_msg="Acceleration mismatch")
