# Dam Break Scenario Matrix — 5 Dams x 3 Scenarios

_Generated: 2026-09-25T16:22:15.891527+00:00 — by `backend/run_dam_matrix.py`_

| Dam | Scenario | SPH 3D | Max depth (m) | Flooded (km²) | Particles | Delft3D-FM |
|-----|----------|--------|---------------|---------------|-----------|------------|
| Bhakra Dam | DAM_BREAK | ✅ COMPLETED | 24.74 | 0.27 | 4582 | 🧱 workspace ready (no dflowfm binary) |
| Bhakra Dam | WATER_RELEASE | ✅ COMPLETED | 23.75 | 0.245 | 4582 | 🧱 workspace ready (no dflowfm binary) |
| Bhakra Dam | RIVER_BLOCKAGE | ✅ COMPLETED | 13.75 | 0.0872 | 3575 | 🧱 workspace ready (no dflowfm binary) |
| Tehri Dam | DAM_BREAK | ✅ COMPLETED | 42.75 | 0.244 | 5105 | 🧱 workspace ready (no dflowfm binary) |
| Tehri Dam | WATER_RELEASE | ✅ COMPLETED | 42.75 | 0.2089 | 5105 | 🧱 workspace ready (no dflowfm binary) |
| Tehri Dam | RIVER_BLOCKAGE | ✅ COMPLETED | 39.24 | 0.1384 | 5889 | 🧱 workspace ready (no dflowfm binary) |
| Hirakud Dam | DAM_BREAK | ✅ COMPLETED | 8.97 | 0.1329 | 6012 | 🧱 workspace ready (no dflowfm binary) |
| Hirakud Dam | WATER_RELEASE | ✅ COMPLETED | 7.75 | 0.1323 | 6012 | 🧱 workspace ready (no dflowfm binary) |
| Hirakud Dam | RIVER_BLOCKAGE | ✅ COMPLETED | 13.75 | 0.064 | 2529 | 🧱 workspace ready (no dflowfm binary) |
| Sardar Sarovar Dam | DAM_BREAK | ✅ COMPLETED | 19.38 | 0.2455 | 6534 | 🧱 workspace ready (no dflowfm binary) |
| Sardar Sarovar Dam | WATER_RELEASE | ✅ COMPLETED | 18.75 | 0.2248 | 6534 | 🧱 workspace ready (no dflowfm binary) |
| Sardar Sarovar Dam | RIVER_BLOCKAGE | ✅ COMPLETED | 13.75 | 0.0872 | 3575 | 🧱 workspace ready (no dflowfm binary) |
| Mettur Dam | DAM_BREAK | ✅ COMPLETED | 8.97 | 0.1367 | 6304 | 🧱 workspace ready (no dflowfm binary) |
| Mettur Dam | WATER_RELEASE | ✅ COMPLETED | 7.75 | 0.1364 | 6304 | 🧱 workspace ready (no dflowfm binary) |
| Mettur Dam | RIVER_BLOCKAGE | ✅ COMPLETED | 13.75 | 0.0707 | 2762 | 🧱 workspace ready (no dflowfm binary) |

## Terrain sources

| Dam | DEM |
|-----|-----|
| Bhakra Dam | SYNTHETIC_VALLEY (schematic, prototype) |
| Tehri Dam | REAL Copernicus GLO-30 clip (reprojected to UTM) |
| Hirakud Dam | SYNTHETIC_VALLEY (schematic, prototype) |
| Sardar Sarovar Dam | SYNTHETIC_VALLEY (schematic, prototype) |
| Mettur Dam | SYNTHETIC_VALLEY (schematic, prototype) |

## Notes

- **SPH 3D** runs are true 3D weakly-compressible SPH (Tait EOS, 3D cubic-spline
  kernel, 3D artificial viscosity, terrain collision) executed by the internal
  solver in `backend/app/engines/sph/`.
- **Delft3D-FM** entries with status `workspace ready` contain a complete D-Flow FM
  workspace (UGRID mesh `_net.nc`, `.mdu`, structure `.ini`, boundary `.pli/.bc/.ext`).
  They execute automatically once a `dflowfm` installation is present
  (`DELFT3D_INSTALL_DIR` in `backend/app/core/config.py`), or run the workspace
  manually with `dflowfm --autostartstop <mdu>`.
- Scenario physics: DAM_BREAK = full-breach failure of the dam wall;
  WATER_RELEASE = spillway gate opening (narrow release width) / Q(t) boundary in
  Delft3D; RIVER_BLOCKAGE = landslide blockage in the downstream gorge failing at
  t = failure_time (SPH) / dambreak structure timeseries (Delft3D).
- Prototype limits: SPH runs are capped at 8-15 s of simulated time and ~9k
  particles; heads are scaled to 15% of the real dam height (max 30 m) so the demo
  domain (1.4 km) stays meaningful. Real operational studies need larger domains,
  real bathymetry and no caps.