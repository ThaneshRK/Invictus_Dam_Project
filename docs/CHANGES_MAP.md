# Change Map — original `0e5ecbe` → `b8a341a`

Every change made on branch `arena/01a0d90d-invictus-dam-project`, file by file.
View any of these yourself with:

```bash
git diff 0e5ecbe..HEAD -- <path>     # one file, original vs modified
git diff 0e5ecbe..HEAD               # everything
git show 0e5ecbe:<path>              # the ORIGINAL file content, untouched
git checkout 0e5ecbe -- <path>       # restore one file to the original
```

A ready-to-apply patch also lives at `CHANGES.patch` (repo root).

## Backend — SPH 3D implementation

| File | Original | Changed to | Why |
|---|---|---|---|
| `backend/app/engines/sph/engine.py` | `SPHEngine(context)` always built `SPH2DSolver`; hardcoded 5 s duration cap; metadata always said "2D SWE-SPH" | `SPHEngine(context, use_3d=False)`; selects `SPH3DSolver` when `use_3d` or scenario param `{"dimensions": 3}`; duration cap overridable via `duration_cap_s` (default still 5.0 s); metadata reports real dimensionality | The 3D solver existed but was unreachable — this is the missing wiring |
| `backend/app/engines/sph/solver.py` | `SPH3DSolver` passed 4-element bounds (no z limits), never set `state.z_b` | 6-element bounds `[xmin..zmax]` for vertical boundary enforcement; bed elevation seeded at init and updated every step; clear error when the water polygon is fully dry | The 3D grid interpolator reads `state.z_b` — without updates, 3D results were unusable |
| `backend/app/engines/sph/physics.py` | `Physics3DSolver` scattered with `np.add.at`, redundant self-pair/support masks, `linalg.norm` | `np.bincount` scatter, masks removed (cKDTree pairs are already distinct + within 2h; r=0 contributes zero), `einsum` norms — identical maths, ~6× faster steps | 640 ms → 103 ms per step made the 15-run matrix feasible |
| `backend/app/engines/sph/builder.py` | Crashed with `TerrainHandler(nx=50,...)` when no DEM; only read `metadata_`; breach only for DAM_BREAK | Shared `resolve_dataset_path`; working flat-terrain fallback; dam-wall representation for all 3 scenarios (breach / spillway opening / intact wall); passes `duration_cap_s` | Fixed the failing `test_sph_level_3_terrain`; made WATER_RELEASE & RIVER_BLOCKAGE physically meaningful |
| `backend/app/engines/utils.py` | *(new file)* | `resolve_dataset_path()` helper | Real `Dataset` models use `.file_path`/`.metadata_`, test mocks use `.metadata` — one resolver for both |
| `backend/app/api/endpoints/jobs.py` | Only `SPH` and `DELFT3D` accepted | `SPH`/`SPH2D` → 2D, `SPH3D` → `use_3d=True`; better error message lists valid engines | Exposes 3D through the job queue |

## Backend — Delft3D-FM

| File | Original | Changed to | Why |
|---|---|---|---|
| `backend/app/services/delft3d/mesh/generator.py` | `MakeGridParameters` with `upper_right_x/y` only — MeshKernel 8.x ignores those and defaults to 3×3 | Sets `num_columns`/`num_rows` = bounds ÷ resolution | Meshes were silently 16 nodes instead of 3,249 — every Delft3D run would have been meaningless |
| `backend/app/engines/delft3d/builder.py` | DEM path lookup duplicated, `metadata_`-only | Uses `resolve_dataset_path` (2 call sites) | Same robustness fix as SPH builder |

## Backend — new deliverable

| File | What it is |
|---|---|
| `backend/run_dam_matrix.py` | *(new)* 5 dams × 3 scenarios × {SPH3D, Delft3D} runner. Reads the government fixtures, builds per-dam UTM terrain (real Copernicus clip for Tehri, synthetic valley elsewhere), derives parameters from real dam height/hydrology, runs everything without needing the API/DB, writes rasters/GeoJSON/metrics + report. Verified: 15/15 SPH3D COMPLETED |
| `backend/tests/engines/sph/test_sph3d.py` | *(new)* 3D lifecycle test (particles are N×3, mass conserved, inundation produced) + parameter-based 3D selection test |

## Frontend

| File | Original | Changed to | Why |
|---|---|---|---|
| `src/components/ScenarioBuilder.tsx` | Dropdown: `SPH`, `DELFT3D` | `SPH 2D`, `SPH 3D`, `Delft3D` | UI access to the 3D engine |
| `src/api.ts` | Hardcoded `http://localhost:8000` | `API_ORIGIN` resolver (env override → preview proxy → localhost) | Works behind proxies/previews, not only localhost |
| `src/components/Map3DViewer.tsx`, `AssetAlignment.tsx` | `scenegraph: http://localhost:8000/...` for the GLB | Uses `API_ORIGIN` | Same |
| `package.json` (+lock) | `leaflet-draw ^0.4.14` — conflicts with `react-leaflet-draw@0.21` peer dep, **`npm ci` failed for everyone** | `leaflet-draw ^1.0.4` | Fresh installs work again; `tsc --noEmit` verified clean |

## Docs & bookkeeping

| File | Change |
|---|---|
| `docs/simulation/matrix.md` | *(new)* Full approach: architecture diagram, SPH 3D piece-by-piece, Delft3D workspace anatomy, how to enable real `dflowfm`, matrix usage, honest limitations |
| `docs/simulation/sph.md`, `delft3d.md` | Rewritten — both described the code inaccurately (delft3d.md still talked about `.mdf` files and `DELFT3D_HOME`) |
| `README.md` | System components + matrix quick-start section |
| `TECH_STACK.md` | Leaflet-Draw version row |
| `AUDIT_REPORT.md` | Status banner on top marking which audited gaps are now closed (audit kept for history) |
| `.gitignore` | Ignores regenerable heavy matrix outputs (`data/matrix_results/*/`); report + summary stay tracked |
| `data/matrix_results/matrix_report.md`, `matrix_summary.json` | *(new)* The verified 15-run results |

## Restoring the original

Nothing was deleted or overwritten in place — the original lives in git:

```bash
git show 0e5ecbe:backend/app/engines/sph/engine.py   # read original
git checkout 0e5ecbe -- backend/app/engines/sph/engine.py  # restore it
git checkout 0e5ecbe -- .                            # restore everything
```
