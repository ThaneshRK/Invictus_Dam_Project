# Flood HADR Current Implementation Audit

## 1. Executive Summary
The Flood HADR project has a solid architectural foundation with a React frontend, FastAPI backend, and PostgreSQL/PostGIS database. It possesses genuine implementation of complex hydrodynamic solvers (2D SPH, true 3D SPH, and complete Delft3D integration). However, there is a significant "disconnect" between the frontend UI (which collects abstract metadata and relies on mocked validation/readiness) and the backend simulation engines (which require concrete geometric data, datasets, and physical boundaries). Currently, user inputs do not robustly generate the precise physical boundaries required for the simulations to be scientifically valid for the selected location.

## 2. Current Architecture
*   **Frontend**: React, Vite, Deck.gl, React-Leaflet
*   **Backend**: FastAPI, SQLAlchemy (async), PostGIS, BackgroundTasks
*   **Solvers**: 
    *   Custom Python SPH 2D (Depth-averaged SWE-SPH)
    *   Custom Python SPH 3D (Tait equation, true 3D kinematics)
    *   Delft3D (D-Flow FM 1.2.184) via automated workspace building
*   **Data Services**: Bounding-box based Government data providers (e.g., NRLD for dams).

## 3. Current User Flow
*   **Login/start**: MISSING (Bypassed)
*   **Dashboard**: IMPLEMENTED
*   **Projects**: IMPLEMENTED
*   **Create Project**: IMPLEMENTED
*   **Location**: PARTIAL (Allows search via Nominatim or map click)
*   **Dam selection**: IMPLEMENTED (Finds nearby dams via local `dam.zip` dataset)
*   **Reservoir selection**: MISSING
*   **River selection**: MISSING
*   **DEM**: DISCONNECTED (Checked in "Data Readiness" mock, but no upload/selection UI)
*   **Hydrological data**: MOCK/PARTIAL (Only simple floats like Initial Water Level)
*   **Scenario**: PARTIAL (Parameters collected, but lacking complex time-series inputs)
*   **Simulation**: IMPLEMENTED (Runs background jobs with async polling)
*   **Results**: IMPLEMENTED
*   **3D viewer**: IMPLEMENTED (Basic Deck.gl visualization of GLB and GeoJSON)
*   **HADR**: PARTIAL (Fetches real data but uses mock 30% intersection)
*   **Export**: IMPLEMENTED

## 4. Project Creation Flow
**Frontend**: `ProjectWizard.tsx` (Steps 1-8).
**What the user enters**: Name, Description, Type, Lat/Lon (or map click), search query.
**Automatically detected**: Nominatim API for location name matching.
**Government data fetched**: Hits `/projects/{id}/nearby-dams` which calls `NRLDProvider` to load local `dam.zip` and calculate Haversine distance.
**Database Storage**: `Project` table (uuid, name, lat/lon, crs, selected_dam_id).
**After clicking Create**: Calls `/projects/{id}/finalize` -> creates `Scenario` and `InitialCondition` -> triggers async `run_enrichment_job`.
**Flow**: `ProjectWizard.tsx` -> `projects.py (Router)` -> `LocationEnrichmentJob` / `Project` (DB).

## 5. Dam/Reservoir/River Flow
*   **Dam Selection**: User can search and select a nearby dam. Dam metadata (name, state) and `source_record_id` (NRLD No) are retrieved.
*   **Backend Trace**: `selected_dam_id` is saved to the `Project` model.
*   **Crucial Distinction**: Selecting a dam currently only provides UI/database metadata. It **DOES NOT** actively inform the simulation engine of the precise dam geometry or location, as the engines rely entirely on arbitrary bounds and configuration dictionaries (a major disconnect).

## 6. DEM Flow
*   **Where it comes from**: Expects a local file path (`dataset_type == "DEM"`).
*   **UI/Discovery**: Missing from the UI flow. The `ProjectWizard` mocks "Data Readiness" check.
*   **Solver Reaching**:
    *   **Delft3D**: Uses `Delft3DTerrainSampler` to convert DEM to `.xyz` bathymetry if provided in `source_datasets`.
    *   **SPH 2D/3D**: Uses `TerrainHandler` to interpolate elevations.
*   **Flow Diagram**:
    File Upload (Missing) -> Database (Dataset model) -> Scenario `source_datasets` -> `Delft3DTerrainSampler` -> `scenario.mdu` (BathymetryFile).

## 7. Hydrological Data
*   **Capabilities**: The database models (`InitialCondition`, `ControlledReleaseParameters`) support `hydrograph`, `water_level`, `storage`, and `constant_discharge`.
*   **Status**: 
    *   **Time series / Hydrographs**: MISSING / DISCONNECTED.
    *   **Reservoir/River Levels**: MOCK/PARTIAL. Only simple float fields are accepted in the UI.
*   **Flow**: User Input (Float) -> DB (`scenario_params`) -> `Delft3DModelBuilder` (used for `WaterLevIni` or `peak_discharge`).

## 8. Scenario System
Three scenarios are implemented in the DB and Engine Builders:
**1. Catastrophic Dam Break**
*   **Status**: IMPLEMENTED.
*   **Backend**: `DamBreakParameters`.
*   **Delft3D**: Uses native ST_DAMBREAK structure with Verheij-van der Knaap breach algorithm.

**2. Controlled Water Release**
*   **Status**: IMPLEMENTED.
*   **Backend**: `ControlledReleaseParameters`.
*   **Delft3D**: Generates Q(t) hydrograph discharge boundary.

**3. River Blockage / Landslide**
*   **Status**: IMPLEMENTED.
*   **Backend**: `RiverBlockageParameters`.
*   **Delft3D**: Simulates via an elevated terrain blockage + dambreak structure (timeseries algorithm) to model failure.

## 9. SPH 2D
*   **Audit Result**: REAL. 
*   **Implementation**: `PhysicsSolver` implements vectorized pairwise SWE-SPH physics, calculating density, hydrostatic pressure, and artificial viscosity. 

## 10. SPH 3D
*   **Audit Result**: REAL.
*   **Implementation**: `Physics3DSolver` implements true 3D fluid dynamics. Uses Tait equation for pressure, true 3D gravity (`state.acc[fluid_idx, 2] = -self.gravity`), and fills particles vertically (`z`). It is not merely a 3D visualization.

## 11. Delft3D
*   **Audit Result**: REAL.
*   **Trace**: Project -> Scenario -> `Delft3DModelBuilder` -> Generates Mesh -> Samples DEM to XYZ -> Generates Boundaries/Structures -> Writes MDU -> Executed via `DockerDelft3DExecutor` or `HostDelft3DExecutor` -> Generates Output.

## 12. Simulation Jobs
*   **Status**: Implement and runs asynchronously.
*   **Model**: Stores `project_id`, `scenario_id`, `engine`.
*   **Warning**: A simulation *can* accidentally run against a different dam geometry than the one selected by the user. The solvers construct bounding geometries dynamically based on general configuration rather than fetching precise geometries from the `selected_dam_id`.

## 13. GLB / 3D Asset
*   **Status**: IMPLEMENTED (Visual Asset Only).
*   **Details**: Uploaded and stored via `assets.py`. Linked to project. Visible in 3D viewer. It does **NOT** automatically become an SPH boundary or Delft3D mesh.

## 14. 3D Viewer
*   **Current State**: `Map3DViewer.tsx` uses Deck.gl. 
*   **Displays**: GLB model (ScenegraphLayer) and Flood extent polygons (GeoJsonLayer).
*   **Mocks**: Simple 2D polygons are extruded for depth visualization. There are no procedural waves, but there are no actual particle visualizers either.

## 15. GIS
*   **Status**: IMPLEMENTED (Backend).
*   **Details**: `export_service.py` handles converting outputs to standard formats. `exports.py` API allows background processing and downloading of files.

## 16. Government Data
*   **Ingestion**: `NRLDProvider` successfully reads local `dam.zip` shapefile using geopandas. 
*   **Usage**: Used for finding nearby dams during project creation. Other data (Infrastructure, Population) is fetched dynamically based on bounding boxes.

## 17. GEE
*   **Status**: PARTIAL / DISCONNECTED.
*   **Details**: Credentials and basic service exist, but GEE is not actively fetching data to influence the current simulation flow.

## 18. HADR
*   **Status**: PARTIAL / MOCK math.
*   **Trace**: Simulation Output -> Bounding Box -> `hadr_service.py` -> Fetches real population/buildings from API -> **MOCK MATH**: Assumes a hardcoded 30% overlap instead of using `ST_Intersects` on the actual inundation polygon.

## 19. Current Actual Flow
USER 
 ↓
CREATE PROJECT (Name, Lat/Lon) 
 ↓
DAM SELECTION (Matches metadata, saves `selected_dam_id`)
 ↓
SCENARIO PARAMS (Floats)
 ↓
          ❌ DISCONNECTED (Geometry/DEM not passed to engine from selected dam)
 ↓
SIMULATION JOB (Generates mesh based on generic config)
 ↓
DELFT3D/SPH
 ↓
RESULT PROCESSING (Inundation Service)
 ↓
HADR (Real fetch, mock math)
 ↓
3D VIEWER (GLB + Extruded GeoJSON)

## 20. Required Problem-Statement Flow
USER
 ↓
CREATE PROJECT ✓
 ↓
SELECT REAL DAM ✓
 ↓
RESOLVE RESERVOIR ❌
 ↓
RESOLVE RIVER ❌
 ↓
DEFINE STUDY AREA ⚠
 ↓
GET REAL DEM ❌
 ↓
GET HYDROLOGICAL DATA ❌
 ↓
SELECT SCENARIO ✓
 │
 ├── Catastrophic Dam Break ✓
 │
 ├── Controlled Water Release ✓
 │
 └── River Blockage / Landslide ✓
 ↓
VALIDATE INPUTS 🔴
 ↓
GENERATE MODEL INPUTS ⚠ (Configured but needs real geometric linkages)
 ↓
SPH 2D ✓
SPH 3D ✓
Delft3D ✓
 ↓
COMMON RESULTS ✓
 ↓
DEPTH ✓
VELOCITY ⚠
ARRIVAL TIME ⚠
INUNDATION ✓
 ↓
GIS ✓
 ↓
3D VISUALIZATION ⚠ (Needs real particle/mesh rendering, not just extruded polygons)
 ↓
HADR 🔴 (Needs ST_Intersection math)
 ↓
SHP/KML/REPORT EXPORT ✓
 ↓
GEE / SATELLITE VALIDATION ❌

## 21. Gap Matrix

| Requirement | Current Status | Evidence/File | Gap | Priority |
| :--- | :--- | :--- | :--- | :--- |
| Project creation | ✓ | `projects.py` | None | - |
| Dam selection | ✓ | `nrld_provider.py` | None | - |
| Reservoir linking | ❌ | `ProjectWizard.tsx` | UI and DB linkage missing | P1 |
| River linking | ❌ | `ProjectWizard.tsx` | UI and DB linkage missing | P1 |
| Study area | ⚠ | `ProjectWizard.tsx` | Drawn but not strictly enforced to engines | P1 |
| DEM | ❌ | `builder.py` | Engine supports it, UI flow missing | P0 |
| Hydrology | ❌ | `ProjectWizard.tsx` | Time-series ingestion missing | P0 |
| Scenarios 1,2,3 | ✓ | `builder.py`, `models/scenario.py`| None | - |
| SPH 2D | ✓ | `physics.py`, `solver.py` | None | - |
| SPH 3D | ✓ | `physics.py`, `solver.py` | None | - |
| Delft3D | ✓ | `builder.py`, `executor.py` | None | - |
| 3D viewer | ⚠ | `Map3DViewer.tsx` | Basic, needs native particle rendering | P2 |
| GLB | ✓ | `assets.py` | Visual only | - |
| HADR | 🔴 | `hadr_service.py` | Math uses 30% static assumption | P1 |
| Government data | ⚠ | `nrld_provider.py` | Dam works, others unverified | P2 |
| GEE | ❌ | `gee_service.py` | Not integrated into simulation loop | P3 |
| GIS Export | ✓ | `export_service.py` | None | - |

## 22. Scientific Validity Issues
1. **Geometric Disconnect**: Selecting a dam in the UI only saves its ID. The simulation solver runs on arbitrary bounds rather than extracting the exact wall/breach geometry from the selected dam/reservoir spatial data.
2. **Mock HADR Mathematics**: `hadr_service.py` fetches real infrastructure counts for the bounding box but hardcodes a 30% impact multiplier instead of performing a true spatial intersection (`ST_Intersects`) with the flood inundation polygon.
3. **No DEM Ingestion**: The engine allows DEM sampling, but the user flow never provides one, defaulting to flat terrains.
4. **Hydrological Oversimplification**: The UI only allows single floating-point inputs for parameters that require transient hydrographs.

## 23. Recommended Implementation Order
*Do NOT execute these. This is the logical path forward.*
1. **Fix the Data Pipeline (DEM & Hydro)**: Implement DEM upload/retrieval and time-series hydrograph support in the frontend to feed the backend correctly.
2. **Bridge the Geometric Disconnect**: Ensure `selected_dam_id` dynamically defines the actual simulation boundary and breach structures in Delft3D/SPH.
3. **Resolve Reservoir/River**: Implement spatial selection of upstream reservoir and downstream river polygons.
4. **Fix HADR Math**: Replace the 30% assumption with true PostGIS intersections against the simulation output grid.
5. **Enhance Visualization**: Upgrade the 3D viewer to render native SPH particles and Delft3D mesh heatmaps rather than simple extruded polygons.
