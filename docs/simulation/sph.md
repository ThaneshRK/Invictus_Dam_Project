# SPH Numerical Prototype

The Phase 4 SPH solver utilizes smooth particle hydrodynamics for fast, flexible shallow-water/dam-break approximations.

## Formulation
- **Integration**: Semi-implicit Euler for stable velocity/position updates.
- **Kernel**: Cubic Spline kernel (`alpha * (1 - 1.5q^2 + 0.75q^3)`).
- **Neighbor Search**: Implemented via `scipy.spatial.cKDTree` providing `O(N log N)` lookup, significantly avoiding naive `O(N^2)` interactions.
- **Pressure**: Tait's equation of state `P = B * ((rho / rho_0)^7 - 1)`.

## Limitations
This engine is a research prototype prioritizing architecture validation over multi-million particle simulations. 
Currently it handles bounding-box reflections and calculates basic pressure forces without complex viscosity tensors.
