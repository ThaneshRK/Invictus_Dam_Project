# SPH Numerical Prototype

The SPH engine (`backend/app/engines/sph/`) is an internal, pure NumPy/SciPy smooth
particle hydrodynamics solver used for fast, flexible dam-break approximations.

## Two formulations

- **2D SWE-SPH** (`engine: "SPH"` / `"SPH2D"`): depth-averaged shallow-water SPH with
  bed-slope source terms from the DEM.
- **3D WCSPH** (`engine: "SPH3D"` or scenario parameter `{"dimensions": 3}`):
  weakly-compressible SPH with full 3D particle state.

## Formulation (3D)
- **Integration**: Semi-implicit Euler with adaptive `dt` from CFL + force limits.
- **Kernel**: Cubic spline, 3D normalisation `1/(π h³)`; recommended `h ≈ 1.3 × spacing`.
- **Neighbour search**: `scipy.spatial.cKDTree`, symmetric pair lists.
- **Pressure**: Tait equation of state `P = B ((ρ/ρ₀)^7 − 1)`.
- **Viscosity**: Monaghan artificial viscosity with 3D sound speed `c = √(γB/ρ₀)`.
- **Terrain**: bilinear DEM sampling; per-step collision penalty keeps particles
  above the bed; bed elevation tracked per particle for depth spatialisation.
- **Boundaries**: 6-element domain bounds, dynamic breach walls (progressive opening),
  blockage AABBs (river blockage scenario), 30 m/s physical velocity cap.
- **Outputs**: particle cloud → regular grid (max depth, velocity, arrival time) →
  GeoJSON inundation footprint + metrics consumed by the Inundation/Comparison services.

## Performance
- Pair scatter uses `np.bincount` (buffered) rather than `np.add.at` (~5× faster).
- Prototype budget: ≈9 000 particles, 8–15 s simulated time on a 1.4 km domain
  (~100 ms/step single-core). For production scale, port the same kernels to
  DualSPHysics (GPU) behind the existing engine interface.

## Limitations
Research prototype prioritising architecture validation over multi-million-particle
runs; mass-conservation diagnostics are simplified; free surface is implicit
(density-based) rather than tracked explicitly.

See `docs/simulation/matrix.md` for the 5 dams × 3 scenarios matrix runner.
