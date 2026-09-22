# System Audit: Flood Simulation Framework Inventory

This document provides a detailed inventory of the CURRENT implementation of the Flood Simulation Framework.

## 1. Projects Management
**What was implemented?** Project CRUD (Create, Read, Update, Delete) and active project context management.
**Where was it implemented?** 
- Backend: `backend/app/models/project.py`, `backend/app/api/endpoints/projects.py`
- Frontend: `frontend/src/components/Projects.tsx`, `frontend/src/context/ProjectContext.tsx`
**How does it work?** Users can create projects which act as isolated workspaces containing datasets, scenarios, and simulations. The active project ID is stored in React context.
**What components are involved?** FastAPI routing, SQLAlchemy models, React Context, and the `Projects.tsx` component.
**What inputs does it accept?** Project metadata (name, description, location coordinates, boundary geometry).
**What outputs does it produce?** Project records and the active project state for the application.
**How is it connected?** All other entities (datasets, scenarios, jobs) are foreign-keyed to a specific project.

## 2. Scenario Building
**What was implemented?** Definition of hydrological parameters and failure modes (Dam Break, Controlled Release, River Blockage).
**Where was it implemented?** 
- Backend: `backend/app/models/scenario.py`, `backend/app/api/endpoints/scenarios.py`, `backend/app/services/scenario_service.py`
- Frontend: `frontend/src/components/ScenarioBuilder.tsx`
**How does it work?** The user inputs parameter values through a form based on the selected scenario type. These parameters are serialized into JSON and saved to the database.
**What components are involved?** React state hooks, FastAPI endpoints, Pydantic schemas.
**What inputs does it accept?** Variables like initial water level, breach width, breach formation time, failure time, peak discharge.
**What outputs does it produce?** Database entries representing physical boundary conditions for simulations.
**How is it connected?** Scenarios are selected when queueing a simulation job and feed boundary parameters to the solver engine.

## 3. Simulation Job Management
**What was implemented?** Queueing and tracking of physics simulation jobs.
**Where was it implemented?**
- Backend: `backend/app/models/job.py`, `backend/app/api/endpoints/jobs.py`
- Frontend: `frontend/src/components/SimulationJobs.tsx`
**How does it work?** Users trigger a run by selecting an engine (SPH or Delft3D) and a scenario. The backend creates a job record in the database with a pending/running status.
**What components are involved?** API routing, SQLAlchemy Job models, Frontend job listing.
**What inputs does it accept?** Scenario ID, Project ID, Target Engine (SPH/DELFT3D).
**What outputs does it produce?** Job status updates and, eventually, result metadata linking to generated output files.
**How is it connected?** Jobs bridge scenarios to the actual physics solver engines and output results.

## 4. Physics Solvers (Engines)
**What was implemented?** Integrations for SPH (Smooth Particle Hydrodynamics) and Delft3D solvers, plus a base engine abstraction.
**Where was it implemented?**
- Backend: `backend/app/engines/base.py`, `backend/app/engines/sph/`, `backend/app/engines/delft3d/`
**How does it work?** The engines take the scenario parameters and execute mathematical models to simulate water flow. Note: Delft3D requires host binaries; otherwise, it returns a test fixture.
**What components are involved?** Engine wrappers, file I/O operations for passing configuration to binaries.
**What inputs does it accept?** Scenario parameters (JSON/dicts).
**What outputs does it produce?** Output files representing water depth, velocity, and time-series data.
**How is it connected?** Triggered by the Job management system; output files are registered as Results.

## 5. 3D Map Visualization
**What was implemented?** 3D WebGL rendering of maps, flood zones, and particles.
**Where was it implemented?**
- Frontend: `frontend/src/components/Map3DViewer.tsx`
**How does it work?** It utilizes `deck.gl` to render data layers (PolygonLayer, ScatterplotLayer) on top of a `react-map-gl/maplibre` basemap using local raster tiles.
**What components are involved?** Deck.gl components, MapLibre base map, React effects.
**What inputs does it accept?** GeoJSON coordinates for polygons, point data for particles, active project bounds.
**What outputs does it produce?** An interactive 3D WebGL canvas.
**How is it connected?** Pulls data from the active project context and simulation results to visualize spatial data.

## 6. Dataset Management
**What was implemented?** Handling of input data (elevation models, land cover) required for simulations.
**Where was it implemented?**
- Backend: `backend/app/models/dataset.py`, `backend/app/api/endpoints/datasets.py`, `backend/app/services/dataset_service.py`
- Frontend: `frontend/src/components/DataManagement.tsx`
**How does it work?** Allows uploading, linking, and managing geospatial assets.
**What components are involved?** File upload handling, database tracking.
**What inputs does it accept?** Files and metadata.
**What outputs does it produce?** Managed references to geospatial files on the server.
**How is it connected?** Datasets provide the topographical basis (e.g., DEM) for the simulation engines.

## 7. Google Earth Engine (GEE) Integration / Satellite
**What was implemented?** Integration with GEE for satellite data retrieval.
**Where was it implemented?**
- Backend: `backend/gee-credentials.json`, `backend/app/services/gee_service.py`, `backend/app/api/endpoints/satellite.py`
- Frontend: `frontend/src/components/Satellite.tsx`
**How does it work?** Authenticates using service account credentials to fetch satellite imagery or remote sensing data.
**What components are involved?** GEE Python API, FastAPI endpoints, Frontend satellite view.
**What inputs does it accept?** Bounding boxes, date ranges.
**What outputs does it produce?** Imagery links or processed raster data.
**How is it connected?** Used to supplement base datasets or provide recent imagery context for projects.

## 8. HADR (Humanitarian Assistance and Disaster Relief) Impact
**What was implemented?** Assessment and visualization of flood impact on populations and infrastructure.
**Where was it implemented?**
- Backend: `backend/app/models/hadr.py`, `backend/app/api/endpoints/hadr.py`, `backend/app/services/hadr_service.py`
- Frontend: `frontend/src/components/HADRImpact.tsx`
**How does it work?** Evaluates simulation inundation results against geographical data to estimate affected areas.
**What components are involved?** Geospatial intersection logic, reporting schemas.
**What inputs does it accept?** Simulation result boundaries.
**What outputs does it produce?** Impact metrics (e.g., population at risk, buildings affected).
**How is it connected?** Consumes simulation output results.

## 9. Results & Comparison
**What was implemented?** Viewing and comparing outcomes of different simulations.
**Where was it implemented?**
- Backend: `backend/app/models/result.py`, `backend/app/api/endpoints/results.py`, `backend/app/api/endpoints/comparison.py`, `backend/app/services/comparison_service.py`
- Frontend: `frontend/src/components/Comparison.tsx`
**How does it work?** Loads multiple result sets and provides analytical comparisons.
**What components are involved?** Data aggregation logic, comparative UI elements.
**What inputs does it accept?** Multiple result IDs.
**What outputs does it produce?** Comparative metrics and side-by-side visual data.
**How is it connected?** Operates on the outputs generated by the simulation jobs.

## 10. Exports
**What was implemented?** Exporting simulation results and reports.
**Where was it implemented?**
- Backend: `backend/app/models/export.py`, `backend/app/api/endpoints/exports.py`, `backend/app/services/export_service.py`
- Frontend: `frontend/src/components/Exports.tsx`
**How does it work?** Generates downloadable packages of simulation data or analysis reports.
**What components are involved?** File packaging logic, API download endpoints.
**What inputs does it accept?** Result or Project ID.
**What outputs does it produce?** Downloadable files (ZIP, CSV, GeoJSON, etc.).
**How is it connected?** Serves as the final output mechanism for the platform data.
