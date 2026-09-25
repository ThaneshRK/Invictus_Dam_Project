# FLOOD HADR — AUDIT EXISTING 3D DAM ASSET + SPH + DELFT3D INTEGRATION

## 1. INSPECT THE GLB

- **File Name**: `dam_this_is_crazy.glb`
- **File Size**: ~1.48 MB (1,481,936 bytes)
- **GLB Version**: 2
- **Meshes**: 145
- **Nodes**: 148
- **Materials**: 6
- **Textures/Images/Animations**: 0
- **Bounding Box** (approximate):
  - X: -520 to 520
  - Y: -30 to 140
  - Z: -320 to 170
- **Coordinate Origin**: Centered around (0,0,0) with relative node translations.
- **Orientation**: Assumed standard Y-up (from bounding box Y having mostly positive values 140).
- **Units**: Meters (implied by the scale, 1040x170x490 total bounding box).
- **Embedded Metadata**: `{'generator': 'Khronos glTF Blender I/O v4.1.63', 'version': '2.0'}` (Exported from Blender).
- **Embedded Textures**: None.
- **Geographically Referenced**: **NO**. The GLB does not have geographic coordinates. X, Y, Z are not Longitude, Latitude, Elevation.
- **Multiple Components**: Yes.

## 2. DETERMINE WHAT THE GLB REPRESENTS

**STRUCTURAL GEOMETRY:**
- Spillway_Chute_mesh
- Spillway_Pier_01 to 06_mesh
- Stilling_Basin_mesh
- Structural_Details_mesh
- Service_Buildings_mesh
- Service_Tower_mesh
- Walkway_Railings_mesh

**TERRAIN:**
- Terrain_Left_Mesh
- Terrain_Right_Mesh

**DECORATIVE/VISUAL ELEMENTS:**
- Over 100 `Icosphere` meshes and `Cube` meshes.

*(Note: The hydraulic solver must NOT depend on decorative meshes or the baked-in terrain, as they do not match the real-world DEM).*

## 3. AUDIT CURRENT 3D FRONTEND

- **3D viewer**: Currently built using `@deck.gl/react` over `react-map-gl/maplibre`.
- **Existing GLTF/GLB loaders**: **Missing**. No `react-three-fiber` or `ScenegraphLayer` is currently implemented to load the GLB.
- **Terrain rendering**: Native MapLibre 2D basemaps (satellite, dark, etc.). True 3D terrain rendering is missing.
- **Simulation result rendering**: Uses `PolygonLayer` for extruded flood zones and `ScatterplotLayer` for particles.
- **Current Data Flow**: The frontend generates procedural math-based "mock" water waves and particles in `Map3DViewer.tsx` inside a `requestAnimationFrame` loop. It does NOT read actual SPH or Delft3D NetCDF results in the 3D Viewer.

**Summary**: 
- **CURRENT 3D VIEWER**: Deck.GL + MapLibre.
- **CURRENT DATA FLOW**: Procedural math simulation in frontend.
- **SUPPORTED FORMATS**: GeoJSON/Arrays (via DeckGL Layers).
- **MISSING CAPABILITIES**: GLB loading, Real NetCDF/UGRID rendering, 3D Terrain Integration, Real SPH Particle ingestion.

## 4. AUDIT SPH IMPLEMENTATION

**SPH 2D:**
- solver: REAL (Uses `SPHSolver` orchestrator)
- particles: REAL (Uses `ParticleState` and `ParticleType`)
- kernels: REAL (`CubicSplineKernel`)
- neighbors: REAL (`NeighborSearch` using grid/tree)
- terrain: REAL (Uses `TerrainHandler` to calculate `z_b` and `grad_z`)
- scenario initialization: REAL (`init_real_scenario` filters DEM based on water polygon)
- breach: REAL (`DynamicBreach` supported in `BoundaryHandler`)
- boundary conditions: REAL
- timestep: REAL (`TimeIntegrator`)
- outputs: REAL (Outputs to files/memory)

**SPH 3D:**
- solver: MISSING (The arrays are heavily 2D, e.g., `acc[:, 0]` and `acc[:, 1]`)
- particles: PARTIAL (Only tracks x, y, and z_bed)
- vx/vy/vz: MISSING (Only 2D velocities are computed)
- density: REAL (2D density)
- pressure: REAL (2D pressure)
- acceleration: PARTIAL (2D only)
- 3D kernel: MISSING
- 3D neighbor search: MISSING
- terrain boundary: PARTIAL (Terrain acts as a 2D bottom friction/gradient, not a full 3D boundary)
- free surface: MISSING (Assumes depth-averaged SWE)
- initialization: MISSING
- outputs: MISSING

## 5. AUDIT DELFT3D IMPLEMENTATION

- dflowfm executable: REAL (Requires external Docker image or host installation).
- Delft3D adapter: REAL (`builder.py` and `executor.py`).
- mesh generation: REAL (`delft3d/mesh/generator.py`).
- DEM conversion: REAL (`TerrainSampler`).
- initial conditions / boundary conditions: REAL (`boundaries.py`).
- execution: REAL (`HostDelft3DExecutor` and `DockerDelft3DExecutor` run asynchronous subprocesses).
- NetCDF output: REAL (Produces `*_map.nc`).
- result parser: REAL (`parser.py` reads `*_map.nc` using NetCDF4/xarray).
- GIS conversion: REAL (`Delft3DGISExporter`).

**Conclusion**: The Delft3D pipeline is mostly REAL and executable, assuming the `dflowfm` engine is available in the environment.

## 6. AUDIT CURRENT PROJECT INPUT SYSTEM

**Frontend Input** (React) -> **API** (FastAPI) -> **Database** (PostgreSQL) -> **Simulation Job** -> **SPH/Delft3D**

- **Frontend Input**: Collects `latitude`, `longitude`, `crs`, `selected_dam_id`, `selected_reservoir_id`, `selected_river_id`, `dem_dataset_id`.
- **API/Database**: Handled by `schemas/project.py` and `models/project.py`. Data is stored as raw fields.
- **Simulation Job**: `ScenarioService` pulls project variables and feeds them into the Engine (SPH/Delft3D).

**Missing Links**:
- No standard way to ingest a 3D asset (GLB) with transformations (Scale, Rotation, Anchor Lat/Lng).
- No translation layer between the raw GLB coordinates (meters around origin) and the simulation domain coordinates.

## 7. DETERMINE HOW THE GLB SHOULD BE USED

**A. VISUAL DAM MODEL**
The GLB should be rendered purely in the 3D viewer (via DeckGL `ScenegraphLayer` or `react-three-fiber`).

**B. HYDRAULIC DAM GEOMETRY**
The GLB **cannot** and **should not** be used directly for hydraulic simulation. It contains non-watertight meshes, decorative objects, and baked-in generic terrain that contradicts real-world DEMs.
**Recommendation**: Derive hydraulic geometry from the real DEM + Dam Footprint Polygon + Scenario parameters.

**C. REAL-WORLD GEOREFERENCING**
The GLB is not georeferenced. It must be visually anchored to the correct geographic location.

## 8. GEOREFERENCING STRATEGY

Create a `Dam3DAsset` schema/model:

```python
class Dam3DAsset:
    asset_id: UUID
    project_id: UUID
    file_path: str
    asset_format: str = "GLB"
    origin_lat: float
    origin_lon: float
    origin_elevation: float
    rotation_x: float
    rotation_y: float
    rotation_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    source: str
    units: str = "meters"
    coordinate_reference_system: str
```
Do not modify the original `.glb` file. Apply the transformation strictly in the frontend rendering layer using metadata.

## 9. DAM ANCHORING

The 3D Viewer should take the `Dam3DAsset` metadata and transform the GLB model matrix:
1. Translate GLB origin to `[origin_lon, origin_lat, origin_elevation]` (using DeckGL `coordinateSystem: COORDINATE_SYSTEM.LNGLAT`).
2. Apply `rotation_x`, `rotation_y`, `rotation_z` (Euler angles).
3. Apply `scale_x`, `scale_y`, `scale_z`.

## 10. GLB + DEM ALIGNMENT

Create a "3D Asset Alignment" UI in the frontend:
- **Display**: The base map/DEM + The loaded GLB.
- **Controls**: Sliders for X/Y/Z rotation, scaling, and a map click-handler to set the Anchor (Lat/Lon).
- **Buttons**: `[Save Alignment]` and `[Reset]`.

## 11. GLB + SPH

**Do NOT force the GLB into SPH.**
The SPH solver is currently a 2D depth-averaged SWE implementation. Using a 3D GLB boundary is incompatible and computationally unfeasible without heavy processing.
Use `DEM + dam footprint + breach geometry` for the hydraulic SPH boundary. The GLB remains for visualization only.

## 12. GLB + DELFT3D

**Do NOT assume the GLB can directly become a Delft3D mesh.**
Delft3D uses 1D/2D/3D flexible meshes (UGRID). The GLB is a visual asset consisting of un-optimized polygons. 
Pipeline: `DEM + River Polygon + Dam Footprint -> Delft3D Mesh Generation (d-flow fm net)`.
The GLB is layered *on top* of the NetCDF simulation results in the 3D Viewer.

## 13. 3D SIMULATION VISUALIZATION

Architecture for the viewer:
- BASE LAYER: `TerrainLayer` / `TileLayer` (MapLibre/DeckGL)
- ASSET LAYER: `ScenegraphLayer` (Dam GLB)
- RESULT LAYER: `PolygonLayer` / `GeoJsonLayer` (Delft3D Depth/Velocity)
- PARTICLE LAYER: `ScatterplotLayer` (SPH Particles)

## 14. SCENARIO ANIMATION

- Timeline control exists in frontend (`time` state variable).
- Replace the procedural `Math.sin()` animation with actual timeseries data fetched from the backend (NetCDF arrays converted to JSON/GeoJSON frames).

## 15. COMMON COORDINATE SYSTEM

Store Project CRS explicitly (e.g., `EPSG:32643` for UTM zones).
API/GIS interoperability uses `EPSG:4326` (WGS84 Degrees).
Mesh generation and SPH **must** be executed in the local Project CRS (Meters) to compute correct physics (Gravity, Area, Volumes).

## 16. COMMON SIMULATION RESULT CONTRACT

Ensure both SPH and Delft3D emit a common JSON/GeoJSON structure to the frontend:
```json
{
  "timestamp": 0,
  "nodes": [
    {"x": 77.8, "y": 11.7, "depth": 5.4, "velocity": [1.2, 0.5], "arrival_time": 10}
  ]
}
```
Delft3D will keep its native `.nc` files for deep analysis.

## 17. UNIFIED SIMULATION PIPELINE

```text
PROJECT
   │
   ├── Location, Dam, Reservoir, River, DEM, Hydrology, Scenario
   │
   ↓
SCENARIO ENGINE
   │
   ├──────────┬──────────┐
   ↓          ↓          ↓
SPH 2D      SPH 3D    DELFT3D-FM
   │          │          │
   └──────────┴──────────┘
   ↓
COMMON RESULTS PARSER
   │
   ├──────────────┐
   ↓              ↓
  GIS         3D VIEWER
                  │
              DAM GLB (Asset)
                  +
              FLOOD DATA (Results)
                  +
              TERRAIN (DEM)
```
