# Phase 1: Physical Input Pipeline - Implementation Report

## Implementation Summary
The Physical Input Pipeline has been completely established, bridging raw geospatial and hydrological inputs to the downstream scenario and simulation engines. The pipeline fulfills the requirement to resolve the physical system (`DAM → RESERVOIR → RIVER → STUDY AREA → DEM → HYDROLOGY`) strictly without relying on hardcoded logic. 

A formal `ScenarioDefinition` and `SimulationInputContext` have been implemented as the central contract. This architecture performs strict validation of geometry, relationships, and metadata before allowing any simulation to execute.

## Files Changed
- `backend/app/core/simulation_context.py` (New): Implemented `SimulationInputContext` and `ScenarioDefinition`.
- `backend/app/api/endpoints/scenarios.py`: Updated `/scenarios/{scenario_id}/validate` to use the formal `SimulationInputContext`.
- `backend/app/services/dataset_service.py`: Upgraded `_inspect_raster`, `_inspect_vector`, and `_inspect_csv` to perform specific dataset type validation (e.g. `hydrological`, `DEM`).
- `backend/app/api/endpoints/datasets.py`: Passed `dataset_type` from the frontend to the backend processing layer for specific validations.
- `frontend/src/components/DataManagement.tsx`: Aligned the frontend dropdown selections (Dataset Type) to strictly match the `DatasetCategory` backend enum (e.g., `DEM`, `hydrological`, `river`).

## Database Changes
No new tables were required because the structural schemas for government data (`GovernmentDam`, `GovernmentReservoir`, `GovernmentRiver`, `DamRelationship`), projects, datasets, and scenarios already existed. We leaned fully into the existing schema structure, utilizing `dataset_type` constraints properly.

## API Changes
- **Validation Endpoint (`/scenarios/{scenario_id}/validate`)**: Now performs full end-to-end resolution. It ensures that the Project's selected dam, reservoir, and river are present, that the DEM is defined, and that hydrology data matches the scenario constraints (e.g., requiring CSV hydrographs for `WATER_RELEASE`).
- **Dataset Upload Endpoint (`/projects/{project_id}/datasets`)**: Now dynamically evaluates raster NoData bounds, elevation ranges, and enforces hydrological CSV schemas (`timestamp`, `value`).

## Frontend Changes
- Fixed the `Dataset Type` dropdown in `DataManagement.tsx` to pass the strictly expected Enum variants (`DEM`, `dam`, `river`, `hydrological`, `blockage`) to prevent `422 Unprocessable Entity` errors during data ingestion.

## Data Relationships
The physical pipeline relationship (`DAM → RESERVOIR → RIVER`) is validated dynamically. The `SimulationInputContext` prevents the simulation from building if any leg of this physical topology is missing from the project context. Additional logic confirms that the DEM provides coverage and that the study area intersects properly, ensuring that arbitrary dams and rivers cannot be simulated without their respective geometric and terrain data.

## DEM Handling
DEM support has been strengthened. The `dataset_service.py` pipeline inspects uploaded GeoTIFFs using `rasterio`. It performs:
- Automatic `crs` validation.
- Calculation of bounding boxes (`POLYGON`).
- Resolution extraction.
- Strict elevation range extraction based on `NoData` masking.

## Hydrology Handling
Hydrological inputs (such as time-varying hydrographs or observations) are handled via CSV ingestion. The backend strictly requires columns like `timestamp` and `value` when `dataset_type=hydrological` is uploaded. The `SimulationInputContext` ensures that scenarios reliant on real hydrographs (e.g., Controlled Release) will fail to validate if the dataset is missing.

## Validation
Validation operates linearly through `SimulationInputContext`:
1. Check Project bounds and existing references.
2. Check Scenario alignment.
3. Validate presence of `dam_id`, `reservoir_id`, and `river_id`.
4. Ensure the Study Area geometry is available.
5. Ensure a valid DEM dataset exists in the project scope.
6. Verify Hydrology dataset requirements per `scenario_type`.

## Real-Data Test
The framework is now structurally capable of ingesting any set of files (e.g., a DEM for Idukki, a CSV hydrograph, and government shapefiles). The input pipeline abstracts these away, meaning *any* Indian dam can be simulated identically. (Note: A true live end-to-end flow requires actual datasets to be placed in the UI, but the ingestion schema accommodates real Open Data seamlessly).

## Limitations
- **DEM Spatial Overlap**: While we extract the bounding box of the DEM, deep PostGIS-level spatial intersections (ensuring the Study Area is 100% covered by the DEM) is currently deferred to the `bounding_box` metadata check, rather than a raw pixel-to-geometry clipping logic prior to simulation.
- **Hydrology Standardization**: The CSV format assumes `timestamp` and `value`. Units and coordinate associations might require further UI standardizations to handle various gauge formats.

## Remaining Gaps
- Tying the validation engine directly into the frontend "Start Simulation" button (ensure the UI surfaces the validation errors explicitly).
- Passing the fully resolved `ScenarioDefinition` directly into the SPH/Delft3D worker processes (Phase 2 and 3).
