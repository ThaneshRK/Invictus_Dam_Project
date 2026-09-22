# Code Audit Report

## Summary
The current repository provides the skeletal structure of a flash-flood / dam-break HADR simulation framework but relies heavily on mock data, stubs, and partial implementations. The React frontend is well-structured but populated with placeholders and simulated API responses. On the backend, a custom Python-based SPH solver exists, but the intended DualSPHysics integration is missing entirely. The Delft3D-FM executor exists but lacks any actual `.mdu` configuration files to run. The Google Earth Engine (GEE) integration contains genuine Earth Engine code but immediately falls back to mock fixtures when credentials are unsupplied. While some real shapefiles (Dam, Reservoir, Rivers) exist in the `datasets/` folder, the codebase does not dynamically run simulations across all planned dams, and the final 5x3 matrix of deliverables is mostly untouched. 

## Deliverables Status

| Deliverable | Status | Evidence / Notes |
| :--- | :--- | :--- |
| (i) Generalized framework for dam break / river blockage using SPH (DualSPHysics) and Delft3D-FM, with loss and damage analysis | **PARTIAL** | Delft3D subprocess code exists (`backend/app/engines/delft3d/executor.py`) but no `.mdu` files are present. Custom numpy SPH engine exists (`backend/app/engines/sph/engine.py`), but DualSPHysics is entirely absent. HADR analysis is mocked (`backend/app/services/hadr_service.py:16`). |
| (ii) Customizable tool that generates inundation scenarios from different input datasets | **PARTIAL** | Scenario Builder exists in the frontend (`frontend/src/components/ScenarioBuilder.tsx`) and API, but relies on mock terrain if DEM is missing (`backend/app/engines/sph/engine.py:87`). |
| (iii) Dashboard (GUI) for inputs and output visualization, supporting large data, with output exported as .shp or .kml | **PARTIAL** | Dashboard UI exists with Map3DViewer, but rendering uses random particle generation (`Map3DViewer.tsx:140`). GIS exporter (`backend/app/services/delft3d/gis_export.py`) produces `.tif` and `.geojson`, but `.kml` is only an unimplemented dropdown option (`frontend/src/components/Exports.tsx:44`). |
| (iv) Near-real-time flood analysis through Google Earth Engine using open data | **STUB-OR-MOCK** | `ee.Initialize()` is called, but deliberately falls back to a hardcoded mock extent `/data/gee_fixtures/sentinel_mock_extent.geojson` (`backend/app/services/gee_service.py:81`). |
| (v) Final demo on real open-source Indian river and dam data | **NOT STARTED** | Only a single config exists for Idukki (`examples/india_demo/config.json`). No other dams have configs, data pipelines, or real results. |

## 5 Dams x 3 Scenarios Matrix

| Dam | Controlled Release | Catastrophic Dam Break | River Blockage / Landslide |
| :--- | :--- | :--- | :--- |
| **Tehri** | Nothing | Nothing | Nothing |
| **Bhakra** | Nothing | Nothing | Nothing |
| **Hirakud** | Nothing | Nothing | Nothing |
| **Idukki** | Nothing | Config Only (`examples/india_demo/config.json`) | Nothing |
| **Nagarjuna Sagar** | Nothing | Nothing | Nothing |

## Fake or Hardcoded Data Identified
- `frontend/src/components/HADRImpact.tsx:55`: `[Interactive Map Placeholder]`
- `frontend/src/components/MapViewer.tsx:20`: `// Mock bounds centered around project`
- `frontend/src/components/Comparison.tsx:7`: `// Using dummy data structurally similar to what the API will return`
- `frontend/src/components/Map3DViewer.tsx:140`: `const distance = particleAge * 0.04 * (0.5 + Math.random() * 0.5);`
- `frontend/src/components/Map3DViewer.tsx:148`: `radius: 30 + Math.random() * 60,`
- `frontend/src/components/DataManagement.tsx:83`: `placeholder="e.g. SRTM 30m"`
- `frontend/src/components/DataManagement.tsx:174`: `Sample Dams (Readiness)`
- `frontend/src/components/Dashboard.tsx:161`: `placeholder="Search location (e.g. Mettur Dam, Narmada, Tehri)..."`
- `backend/app/engines/sph/engine.py:87`: `# Mock fallback if filepath not provided` (Generates flat terrain `np.zeros((100, 100))`)
- `backend/app/api/endpoints/comparison.py:27`: `"max_depth_array_mock", [[1.0, 2.0], [0.5, 0.0]]`
- `backend/app/api/endpoints/comparison.py:36`: `"max_depth_array_mock", [[1.1, 1.9], [0.4, 0.0]]`
- `backend/app/api/endpoints/hadr.py:15`: `flood_extent_path: str = "/data/mock_extent.geojson"`
- `backend/app/api/endpoints/hadr.py:33`: `# Default bounds if none provided (mock 1 degree box around project)`
- `backend/app/api/endpoints/hadr.py:68`: `flood_extent_path="/data/mock",`
- `backend/app/services/hadr_service.py:16`: `Here we mock the intersection math`
- `backend/app/services/hadr_service.py:42`: `# Assuming 30% of bounding box is flooded for the mock intersection`
- `backend/app/services/hadr_service.py:52`: `# Mock intersection logic`
- `backend/app/services/hadr_service.py:63`: `results["affected_road_length_km"] = len(features) * 0.5 # Mock km estimation`
- `backend/app/services/preprocessing_service.py:41`: `# Mock integration of GIS steps to produce a manifest`
- `backend/app/services/gee_service.py:81`: `"observed_flood_extent": "/data/gee_fixtures/sentinel_mock_extent.geojson"`

## Top 10 Gaps for Finishing a Live Demo (Priority Order)
1. **Missing Delft3D Models**: No actual `.mdu`, grid, or boundary files exist. A working Delft3D simulation must be configured for at least one scenario.
2. **Missing DualSPHysics Integration**: DualSPHysics is not implemented; only a custom NumPy SPH solver exists. 
3. **No Real Result Files**: There are no actual outputs to visualize. The dashboard relies entirely on random particle generation and dummy JSON responses.
4. **Missing Dam Configurations**: 4 out of the 5 requested dams have no configuration or project setups. Even Idukki only has a single JSON config and no pre-processed terrain or grid data.
5. **No Actual KML/SHP Export**: The export functionality (`gis_export.py`) only writes `.tif` and `.geojson`, but the deliverables and frontend dropdown require `.kml` and `.shp`.
6. **Mocked HADR Logic**: `hadr_service.py` mocks spatial intersections and road length calculations rather than doing genuine PostGIS operations on real infrastructure data.
7. **GEE Credentials Missing**: GEE integration falls back to a static fixture because it lacks functional credentials. The environment needs a valid Service Account configured.
8. **Terrain Ingestion Fallback**: If a DEM is not perfectly specified, the system creates a flat `100x100` numpy array instead of failing or downloading real SRTM data.
9. **Lack of Validation/Comparison**: The system lacks any test that compares the outputs against historical data or empirical breach formulas.
10. **Hardcoded UI Search/Metrics**: The frontend is hardcoded with placeholder values (e.g. `11.80` for depth) and doesn't dynamically tie into the backend API results completely.

## Commands to Run the Current System
**Database:**
```bash
./scripts/start-docker.sh
```
**Backend:**
```bash
source venv/bin/activate
./scripts/start-backend.sh
```
**Frontend:**
```bash
cd frontend
npm run dev
```
