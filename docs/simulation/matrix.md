# 5 Dams × 3 Scenarios Matrix — SPH 3D + Delft3D-FM

This document describes how the two hydraulic engines are implemented and wired into the
platform, and how the complete **5 dams × 3 scenarios × 2 engines** deliverable matrix is
produced.

```
                 ┌───────────────────────────────────────────────────┐
                 │  Government static fixtures (5 dam systems)       │
                 │  data/fixtures/government/{dams,hydrology,...}    │
                 └──────────────────────┬────────────────────────────┘
                                        ▼
                    per-dam terrain (UTM metres, 10 m grid)
                    • Tehri: REAL Copernicus GLO-30 clip
                    • others: synthetic schematic valley DEM
                                        ▼
        ┌───────────────────────┬───────────────────────────┐
        ▼                       ▼                           ▼
   DAM_BREAK              WATER_RELEASE               RIVER_BLOCKAGE
   (dam wall fails,       (spillway gates open a      (landslide blockage in
    breach erosion)        narrow release width)       gorge fails at t_f)
        └───────────┬───────────┴───────────┬───────────┘
                    ▼                       ▼
          SPH 3D (internal)        Delft3D-FM (adapter)
          true 3D WCSPH            UGRID mesh + MDU + structures
          Tait EOS, 3D kernel      + boundary forcing (.pli/.bc/.ext)
                    └───────────┬───────────┘
                                ▼
        common outputs: max depth raster, inundation GeoJSON,
        metrics JSON, matrix_report.md / matrix_summary.json
```

## 1. SPH 3D — how it is implemented

Everything lives in `backend/app/engines/sph/` (pure NumPy/SciPy, no external solver):

| Piece | File | 3D support |
|---|---|---|
| Particle state | `particle.py` | N×3 position/velocity/acceleration arrays |
| Kernel | `kernel.py` | 3D cubic-spline normalisation `1/(π h³)` |
| Neighbours | `neighborhood.py` | `cKDTree` in 3D, symmetric pair lists |
| Physics | `physics.py` → `Physics3DSolver` | Tait EOS (`γ=7`), 3D pressure gradient, Monaghan artificial viscosity with 3D sound speed |
| Terrain | `boundary.py` → `TerrainHandler` | bilinear bed elevation; per-step collision penalty pushes particles out of the bed |
| Boundaries | `boundary.py` → `BoundaryHandler` | 6-element bounds `[xmin,xmax,ymin,ymax,zmin,zmax]`; dynamic breach walls; blockage AABBs |
| Time integration | `integrator.py` | CFL + force-limited adaptive `dt`, semi-implicit Euler, 30 m/s physical velocity cap |
| Results | `writer.py` + `spatialization.py` | 3D particle cloud → per-cell max free-surface − bed = max depth grid, arrival time, GeoJSON footprint |

**Engine selection** (`app/api/endpoints/jobs.py`):

- `engine: "SPH"` or `"SPH2D"` → 2D depth-averaged SWE-SPH
- `engine: "SPH3D"` → `SPHEngine(context, use_3d=True)` → `SPH3DSolver`
- Scenario parameter `{"dimensions": 3}` also selects the 3D solver.

The Scenario Builder dropdown in the dashboard exposes all three engines.

**Performance notes** (pure-NumPy prototype):

- Kernel ratio `h ≈ 1.3 × particle_spacing` (standard for cubic splines; larger ratios
  explode the neighbour count in 3D).
- Pair scatter uses `np.bincount` instead of `np.add.at` (identical maths, ~5× faster).
- Budget ≈ 9 000 particles, 8–15 s of simulated time per run on the 1.4 km demo domain.

## 2. Delft3D-FM — how it is implemented

The adapter in `backend/app/engines/delft3d/` builds a **complete, executable D-Flow FM
workspace** for every scenario:

- `builder.py` — orchestrates the workspace:
  - `services/delft3d/mesh/generator.py` → UGRID `_net.nc` via **MeshKernel**
    (rectangular unstructured grid; `num_columns/num_rows` derived from bounds+resolution)
  - `services/delft3d/terrain/sampler.py` → `bathymetry.xyz` sampled from the DEM
  - `services/delft3d/forcing/structure_generator.py` → `structures.ini` + `.pli`
    (ST_DAMBREAK, Verheij–van der Knaap breach growth for DAM_BREAK; breach-timeseries
    structure for RIVER_BLOCKAGE)
  - `services/delft3d/forcing/boundaries.py` + `ext_generator.py` → discharge/water-level
    `.bc` time series registered in the `.ext` forcing file (WATER_RELEASE)
  - `scenario.mdu` matching D-Flow FM 1.2.x
- `executor.py` — runs `dflowfm` as a subprocess (host install or Docker image).
- `parser.py` — reads the `*_map.nc` NetCDF output back into the common result format.

**Physical model**: 2D depth-averaged shallow water (Kmx=0). D-Flow FM is the
industry-standard complement to the particle-based SPH prototype — the Comparison tab
can quantify IoU/RMSE/MAE between the two footprints.

### Executing Delft3D for real

The builder always runs; execution requires the Deltares binary:

1. Install D-Flow FM (source build or the `delft3d:dflowfm` Docker image).
2. Set in `backend/app/core/config.py` / `.env`:
   - `DELFT3D_INSTALL_DIR=/path/to/install` (host mode) **or**
   - `DELFT3D_EXECUTION_MODE=docker` + `DELFT3D_CONTAINER_IMAGE=...`
3. Re-run the matrix — runs flip from `WORKSPACE_READY_NO_BINARY` to `COMPLETED`,
   and NetCDF results are parsed automatically.

Manual execution of any generated workspace also works:

```bash
cd data/matrix_results/delft3d_workspaces/job_tehri_dam_break
dflowfm --autostartstop scenario.mdu
```

## 3. The matrix runner

```bash
# full matrix (≈25–35 min: 15 SPH 3D runs + 15 Delft3D workspace builds)
.venv/bin/python backend/run_dam_matrix.py

# subsets
.venv/bin/python backend/run_dam_matrix.py --dams tehri bhakra
.venv/bin/python backend/run_dam_matrix.py --scenarios DAM_BREAK --engines SPH3D
```

| Dam | River | State | Terrain |
|---|---|---|---|
| Bhakra | Sutlej | Himachal Pradesh | synthetic valley |
| Tehri | Bhagirathi | Uttarakhand | **real** Copernicus GLO-30 clip |
| Hirakud | Mahanadi | Odisha | synthetic valley |
| Sardar Sarovar | Narmada | Gujarat | synthetic valley |
| Mettur | Cauvery | Tamil Nadu | synthetic valley |

Scenario parameters are derived per dam from the static government fixtures
(`data/fixtures/government/`): dam height → prototype head (15% of height, capped at 30 m) and
USBR-style breach width (3x height, capped at 140 m), hydrology fixture →
release/inflow discharges.

### Outputs (`data/matrix_results/`)

```
{dam}/inputs/dem.tif                     terrain used (UTM, 10 m)
{dam}/{scenario}/run_result.json         parameters + both engine results
{dam}/{scenario}/sph3d_result.json       (inside run_result.json under "SPH3D")
{dam}/{scenario}/sph3d_max_depth.tif     max-depth raster (UTM)
{dam}/{scenario}/sph3d_inundation.geojson  footprint (WGS84, ready for the dashboard)
delft3d_workspaces/job_{dam}_{scenario}/ full D-Flow FM workspace
matrix_summary.json                      machine-readable matrix
matrix_report.md                         human-readable 5×3 report
```

## 4. Honest limitations

- SPH runs are a **prototype scale**: 1.4 km domain, ~9 k particles, ≤15 s of simulated
  time, heads scaled to 15% of real dam height (max 30 m). Real dam-break studies need km-scale domains, real
  bathymetry, dual-GPU DualSPHysics or similar, and hours of simulated time.
- Synthetic DEMs are schematic V-valleys — only Tehri uses real terrain. Drop real DEM
  GeoTIFFs into `{dam}/inputs/dem.tif` (or attach them as project datasets in the
  dashboard) to upgrade any dam.
- The dam **GLB model** (`dam_this_is_crazy.glb`) is a visualization asset anchored via
  `Dam3DAsset` metadata in the 3D viewer; it deliberately does not feed the solvers
  (non-watertight decorative meshes) — hydraulic geometry comes from DEM + fixtures.
