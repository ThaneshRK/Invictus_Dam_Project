# Phase 2: Engine Connectivity Report

## 1. Engine Audit Summary Before Phase 2
Before Phase 2, `run_simulation_task` manually constructed an arbitrary dictionary `config`. Engines relied heavily on this dictionary, utilizing hardcoded geometries (e.g. `dam_x = xmin + width*0.33`) and fallback mocks (e.g. `np.zeros(100,100)`) whenever the physical truth was absent.

## 2. Input Source After Phase 2
`SimulationInputContext` has now been strictly enforced as the **single source of truth** for all numerical engines (SPH2D, SPH3D, Delft3D).

### Key Implementation Changes:
- **`SimulationInputContext` Enforcement**: `SPHEngine` and `Delft3DEngine` have been refactored to accept a strongly-typed `SimulationInputContext` instead of an arbitrary dictionary `config`.
- **`SPHInputBuilder` Introduced**: A dedicated adapter class (`backend/app/engines/sph/builder.py`) processes the Context geometries and translates them to SPH coordinate bounds, terrain objects, water polygons, and dynamic breaches. Hardcoded fallbacks inside the engine have been completely removed.
- **`Delft3DModelBuilder` Refactored**: The builder (`backend/app/engines/delft3d/builder.py`) now inherently queries `SimulationInputContext` to map `dam.geometry`, `reservoir.geometry`, and `river.geometry` into spatial grids, generating boundaries without defaulting to artificial domain coordinates.
- **Removal of Fallback Generation**: If a DEM, study area, or essential GIS artifact is absent, engines immediately fail with a deterministic `ValueError` rather than silently continuing with a mock `np.zeros` array.
- **Test Alignment**: All integration and unit tests (`tests/engines/test_sph.py`, `tests/test_delft3d_scenarios.py`) were modernized to utilize `MockContext`, asserting structural guarantees over engine initialization interfaces. Live hydro-dynamic execution in Delft3D is deliberately skipped in test environments where physical DEM data isn't supplied, preventing synthetic geometry crashes.

## 3. Post-Phase 2 Status Matrix

| ENGINE | INPUT | PHASE 2 SOURCE OF TRUTH | STATUS |
|--------|-------|--------------------------|--------|
| **SPH2D/3D** | DEM | `SimulationInputContext.dem` | IMPLEMENTED |
| **SPH2D/3D** | Terrain | `SimulationInputContext.dem` | IMPLEMENTED |
| **SPH2D/3D** | Dam geometry | `SimulationInputContext.dam` (Point) | IMPLEMENTED |
| **SPH2D/3D** | Reservoir geometry | `SimulationInputContext.reservoir` (Polygon) | IMPLEMENTED |
| **SPH2D/3D** | River geometry | `SimulationInputContext.river` (LineString) | IMPLEMENTED |
| **SPH2D/3D** | Study Area | `SimulationInputContext.study_area` | IMPLEMENTED |
| **SPH2D/3D** | Discharge/Hydrograph | `SimulationInputContext.hydrology` (CSV) | IMPLEMENTED |
| **Delft3D** | DEM | `SimulationInputContext.dem` | IMPLEMENTED |
| **Delft3D** | Terrain | `SimulationInputContext.dem` | IMPLEMENTED |
| **Delft3D** | Dam geometry | `SimulationInputContext.dam` (Point) | IMPLEMENTED |
| **Delft3D** | Reservoir geometry | `SimulationInputContext.reservoir` (Polygon) | IMPLEMENTED |
| **Delft3D** | River geometry | `SimulationInputContext.river` (LineString) | IMPLEMENTED |
| **Delft3D** | Study Area | `SimulationInputContext.study_area` | IMPLEMENTED |
| **Delft3D** | Hydrograph | `SimulationInputContext.hydrology` (CSV) | IMPLEMENTED |

## 4. End-to-End Simulation Testing State
Real end-to-end execution of `SimulationInputContext` mapping to hydro-dynamic execution currently awaits real-world DEM/hydrology datasets from the user. For Phase 2, unit and integration tests validate the data pipeline connecting Context bounds/geometries to the simulation solver initializations.
