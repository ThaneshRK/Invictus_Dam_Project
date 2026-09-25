# Delft3D-FM Adapter

The Delft3D adapter (`backend/app/engines/delft3d/`) bridges the generalized Scenario
Engine and Deltares **D-Flow FM** (unstructured flexible mesh, 2D depth-averaged,
Kmx=0). It is *not* a re-implementation — it generates a complete, standards-compliant
simulation workspace and executes the official solver as a subprocess.

## Workspace produced per scenario

| Artifact | Generator | Content |
|---|---|---|
| `mesh/domain_net.nc` | `services/delft3d/mesh/generator.py` | UGRID 1.0 rectangular unstructured mesh (MeshKernel; `num_columns/num_rows` from bounds + `mesh_resolution`) |
| `terrain/bathymetry.xyz` | `services/delft3d/terrain/sampler.py` | bed levels sampled from the project DEM |
| `config/structures.ini` + `.pli` | `forcing/structure_generator.py` | DAM_BREAK: ST_DAMBREAK with Verheij–van der Knaap breach growth; RIVER_BLOCKAGE: breach-timeseries structure at the landslide location |
| `boundary/*.pli/.bc`, `*.ext` | `forcing/boundaries.py`, `forcing/ext_generator.py` | WATER_RELEASE: Q(t) discharge boundary + downstream water-level boundary |
| `scenario.mdu` | `builder.py` | D-Flow FM 1.2.x run file referencing all of the above |

## Requirements & configuration (`backend/app/core/config.py`)

- `DELFT3D_ENABLED=True`
- `DELFT3D_EXECUTION_MODE="host"` → `DELFT3D_INSTALL_DIR` must contain
  `bin/run_dflowfm.sh`; **or**
- `DELFT3D_EXECUTION_MODE="docker"` → `DELFT3D_CONTAINER_IMAGE` must exist locally
  (executed with the workspace bind-mounted at `/workspace`).

## Behaviour without an installation

Workspace building always works (mesh/MDU/forcing are pure Python). With no binary
present, the matrix runner reports `WORKSPACE_READY_NO_BINARY` and the generated
workspace can be executed anywhere D-Flow FM is installed:

```bash
dflowfm --autostartstop scenario.mdu
```

## Security
`subprocess.Popen` is invoked with array argument lists only (no shell interpolation),
and every run is confined to its per-job workspace directory with a hard timeout
(`DELFT3D_TIMEOUT_SECONDS`).

## Results
`parser.py` reads the `*_map.nc` NetCDF map output; `Delft3DGISExporter` converts it to
GeoTIFF/GeoJSON footprints for the dashboard, and the Comparison service computes
IoU/RMSE/MAE against the SPH results.

See `docs/simulation/matrix.md` for the 5 dams × 3 scenarios matrix runner.
