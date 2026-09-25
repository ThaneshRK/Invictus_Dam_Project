# Generalized Flood Simulation & HADR Framework

This repository contains the complete end-to-end framework for modeling dam breaches and river blockages, translating raw GIS data into actionable Humanitarian Assistance and Disaster Relief (HADR) insights.

## System Components
1. **FastAPI Backend**: Python 3.11 API for geometry validation, physics orchestration, and data transformation.
2. **React Dashboard**: React/Vite web interface with Leaflet integration.
3. **PostgreSQL/PostGIS**: Spatial relational database.
4. **Physics Engines**:
   - **SPH 2D / SPH 3D** — internal NumPy/SciPy smooth-particle-hydrodynamics solvers
     (depth-averaged SWE-SPH and true 3D weakly-compressible SPH).
   - **Delft3D-FM adapter** — generates complete D-Flow FM workspaces (UGRID mesh, MDU,
     structures, boundary forcing) and executes the official solver when installed.

## 5 Dams x 3 Scenarios Matrix
The complete deliverable matrix (Bhakra, Tehri, Hirakud, Sardar Sarovar, Mettur x
DAM_BREAK / WATER_RELEASE / RIVER_BLOCKAGE x SPH 3D + Delft3D-FM) runs with one command:

```bash
.venv/bin/python backend/run_dam_matrix.py
```

It writes per-run results (max-depth rasters, inundation GeoJSON, metrics), ready-to-run
Delft3D workspaces, and a `data/matrix_results/matrix_report.md` summary. See
`docs/simulation/matrix.md` for the full approach and how to enable real `dflowfm`
execution.

---

## End-to-End Demonstration Guide

### 1. Start the Database
The most reliable way to start the PostGIS database is via Docker:
```bash
./scripts/start-docker.sh
```
This single script spins up the `postgis`, `backend`, and `frontend` securely.

### 2. Start Backend (Local Dev)
If developing locally outside Docker:
```bash
source venv/bin/activate
./scripts/start-backend.sh
```
The API is available at `http://localhost:8000`.

### 3. Start Frontend (Local Dev)
```bash
cd frontend
npm run dev
```
The UI is available at `http://localhost:3000`.

### 4. Create Project
In the Dashboard (or via `POST /api/v1/projects`), define your study area (e.g., "Idukki Dam Analysis") and provide a bounding box.

### 5. Add Datasets
Upload a DEM (GeoTIFF) and Dam infrastructure geometries (GeoJSON) using the Data Management tab.

### 6. Preprocess
The GIS Service validates CRSs, standardizes bounds to the Project window, and prepares arrays for the solver.

### 7. Create Scenario
Select `DAM_BREAK`. Configure reservoir volume, breach width, and simulation timestep.

### 8. Run SPH
Queue the job using the `SPH` engine. The background worker will run the Smooth Particle Hydrodynamics numeric solver.

### 9. Configure/Run Delft3D
If `DELFT3D_HOME` is installed, select `DELFT3D`. The adapter translates the scenario into `.mdf` files and executes them securely via subprocess.

### 10. Generate Inundation
The `InundationService` extracts metrics (Max Depth, Mean Depth, Flooded Area in km²) from the completed simulation outputs, filtering noise below 0.10m.

### 11. Compare Models
Navigate to the Comparison Tab. The service computes IoU, RMSE, and MAE between SPH and Delft3D raster footprints.

### 12. Export SHP/KML
Use the Export Center to convert PostgreSQL spatial references into downloadable Shapefiles or KMLs for Google Earth Pro.

### 13. Run GEE Validation
If Sentinel-1 SAR imagery exists for the date range, the GEE Service intersects observation polygons with simulation extents.

### 14. Run HADR Analysis
The HADR Exposure service intersects the maximum flood depth polygon against OpenStreetMap datasets (Buildings/Roads) to quantify impacted populations WITHOUT inventing monetary values.

### 15. View Results in Dashboard
Inspect all layers concurrently via the Interactive Leaflet Map Viewer.
